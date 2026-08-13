import asyncio
import hashlib
import json
from typing import Literal
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from backend.clients.chatbot_client import ChatbotClient
from backend.models import Generation, User
from backend.services.credit_service import (
    apply_generation_usage_rollback,
    finalize_generation_usage_rollback,
    reserve_generation_usage,
    reset_generation_usage_rollback,
    settle_generation_usage,
)
from backend.schemas import (
    MODEL_RESULT_ADAPTER,
    BasicModelResult,
    BlockedResult,
    ConsultantModelResult,
    ConsultantSourceContext,
    ErrorResult,
    GenerateRequest,
    GenerationResponse,
    GenerationUsage,
    ModelRequest,
    ModelResult,
    StoreContext,
)


class IdempotencyConflict(Exception):
    """같은 Idempotency-Key가 다른 요청 body에 이미 사용되었습니다."""


class SourceGenerationNotFound(Exception):
    """요청 사용자가 소유한 source generation을 찾을 수 없습니다."""


class SourceGenerationConflict(Exception):
    """source generation의 타입 또는 상태가 현재 요청과 호환되지 않습니다."""


class GenerationDataInvariantError(Exception):
    """DB에 저장된 생성/사용자 데이터가 서비스 불변조건을 위반합니다."""


class ModelExecutionError(Exception):
    """모델 실행 또는 저장 결과 검증의 기술 실패입니다."""

    def __init__(
        self,
        *,
        reason: Literal["timeout", "rate_limit", "provider_error", "unknown"],
        message: str,
    ) -> None:
        self.reason = reason
        self.message = message
        super().__init__(message)


def serialize_model_result_for_storage(result: ModelResult) -> str:
    """ModelResult를 secret/image bytes 없이 DB replay용 JSON으로 직렬화합니다."""
    payload = result.model_dump(mode="json", by_alias=True)
    if isinstance(result, BasicModelResult):
        for proposal in payload["proposals"]:
            proposal.pop("image_b64", None)
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def hash_generate_request(request: GenerateRequest) -> str:
    """검증된 Public 요청만 canonical JSON으로 SHA-256 hash합니다."""
    payload = request.model_dump(mode="json", exclude_none=False)
    canonical = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def _required_non_blank(value: str | None, field_name: str) -> str:
    if value is None or not value.strip():
        raise GenerationDataInvariantError(f"{field_name} 값이 필요합니다.")
    return value


def _resolve_source_context(
    db: Session,
    user: User,
    request: GenerateRequest,
) -> ConsultantSourceContext | None:
    if request.source_gen_id is None:
        return None
    if request.chatbot_type != "basic":
        raise SourceGenerationConflict("Consultant 요청은 source_gen_id를 사용할 수 없습니다.")

    source = db.scalar(
        select(Generation).where(
            Generation.id == request.source_gen_id,
            Generation.user_id == user.id,
        )
    )
    if source is None:
        raise SourceGenerationNotFound(request.source_gen_id)
    if source.chatbot_type != "consultant" or source.status != "done":
        raise SourceGenerationConflict(
            "source generation은 완료된 Consultant 결과여야 합니다."
        )
    if source.result_json is None:
        raise GenerationDataInvariantError("완료된 source generation 결과가 없습니다.")

    try:
        raw = json.loads(source.result_json)
        source_result = ConsultantModelResult.model_validate(raw)
    except (json.JSONDecodeError, TypeError, ValidationError) as error:
        raise GenerationDataInvariantError(
            "완료된 Consultant source 결과가 저장 계약을 위반합니다."
        ) from error

    return ConsultantSourceContext(
        generation_id=source.id,
        strategy=source_result.strategy,
        reasons=source_result.reasons,
        sources=source_result.sources,
    )


def build_model_request(
    db: Session,
    user: User,
    request: GenerateRequest,
) -> ModelRequest:
    """Public 요청과 서버 소유 User/Generation 상태로 ModelRequest를 조립합니다."""
    business_name = _required_non_blank(user.business_name, "business_name")
    business_type = _required_non_blank(user.business_type, "business_type")
    road_address = user.road_address
    address = (
        road_address
        if road_address is not None and road_address.strip()
        else user.address
    )
    address = _required_non_blank(address, "address")
    if user.lat is None or user.lng is None:
        raise GenerationDataInvariantError("가게 좌표가 필요합니다.")

    try:
        store = StoreContext(
            name=business_name,
            type=business_type,
            address=address,
            lat=user.lat,
            lng=user.lng,
        )
        source_context = _resolve_source_context(db, user, request)
        return ModelRequest(
            chatbot_type=request.chatbot_type,
            user_id=user.id,
            question=request.question,
            platform=request.platform,
            store=store,
            extra=request.extra,
            source_context=source_context,
        )
    except ValidationError as error:
        raise GenerationDataInvariantError(
            "서버 소유 사용자/가게 정보가 ModelRequest 계약을 위반합니다."
        ) from error


def _restore_stored_result(generation: Generation) -> ModelResult:
    if generation.result_json is None:
        raise GenerationDataInvariantError("저장된 generation 결과가 없습니다.")
    try:
        raw = json.loads(generation.result_json)
        return MODEL_RESULT_ADAPTER.validate_python(
            raw,
            chatbot_type=generation.chatbot_type,
        )
    except (json.JSONDecodeError, TypeError, ValueError, ValidationError) as error:
        raise GenerationDataInvariantError(
            "저장된 generation 결과가 ModelResult 계약을 위반합니다."
        ) from error


def _stored_usage(generation: Generation) -> GenerationUsage:
    try:
        return GenerationUsage(
            plan=generation.plan,
            credits_used=generation.credits_used,
        )
    except ValidationError as error:
        raise GenerationDataInvariantError("저장된 generation usage가 올바르지 않습니다.") from error


def replay_existing_generation(
    generation: Generation,
    request: GenerateRequest,
) -> GenerationResponse:
    """같은 key+same body의 기존 row를 모델 재호출/재과금 없이 복원합니다."""
    if generation.request_hash != hash_generate_request(request):
        raise IdempotencyConflict("같은 Idempotency-Key가 다른 요청에 사용되었습니다.")

    usage = _stored_usage(generation)
    if generation.status in {"pending", "generating"}:
        return GenerationResponse(
            generation_id=generation.id,
            status=generation.status,
            chatbot_type=generation.chatbot_type,
            result=None,
            usage=usage,
        )

    result = _restore_stored_result(generation)
    if generation.status == "failed":
        if isinstance(result, ErrorResult):
            raise ModelExecutionError(reason=result.reason, message=result.message)
        if not isinstance(result, BlockedResult):
            raise GenerationDataInvariantError(
                "failed generation에는 BlockedResult 또는 ErrorResult만 저장할 수 있습니다."
            )
        return GenerationResponse(
            generation_id=generation.id,
            status="failed",
            chatbot_type=generation.chatbot_type,
            result=result,
            usage=usage,
        )

    if generation.status in {"done", "published"}:
        if not isinstance(result, (BasicModelResult, ConsultantModelResult)):
            raise GenerationDataInvariantError(
                "성공 generation에는 성공 ModelResult가 필요합니다."
            )
        return GenerationResponse(
            generation_id=generation.id,
            status=generation.status,
            chatbot_type=generation.chatbot_type,
            result=result,
            usage=usage,
        )

    raise GenerationDataInvariantError("알 수 없는 generation 상태입니다.")


def _normalize_idempotency_key(value: str) -> str:
    try:
        return str(UUID(value))
    except (TypeError, ValueError, AttributeError) as error:
        raise ValueError("Idempotency-Key는 UUID여야 합니다.") from error


def _find_existing_generation(
    db: Session, user_id: int, idempotency_key: str
) -> Generation | None:
    return db.scalar(
        select(Generation).where(
            Generation.user_id == user_id,
            Generation.idempotency_key == idempotency_key,
        )
    )


def _load_generating_generation(
    db: Session, generation_id: int, user_id: int
) -> Generation:
    generation = db.scalar(
        select(Generation).where(
            Generation.id == generation_id,
            Generation.user_id == user_id,
        )
    )
    if generation is None or generation.status != "generating":
        raise GenerationDataInvariantError(
            "generation은 transaction 2 시작 시 generating 상태여야 합니다."
        )
    return generation


def _internal_error(message: str) -> ModelExecutionError:
    return ModelExecutionError(reason="unknown", message=message)


def _failed_error_result(
    reason: Literal["timeout", "rate_limit", "provider_error", "unknown"],
    message: str,
) -> ErrorResult:
    return ErrorResult(status="error", reason=reason, message=message)


def _handle_failed_result(
    db: Session,
    user: User,
    generation_id: int,
    reservation,
    result: BlockedResult | ErrorResult,
    *,
    now,
) -> GenerationResponse:
    generation = _load_generating_generation(db, generation_id, user.id)
    generation.status = "failed"
    apply_generation_usage_rollback(db, user.id, reservation, now)
    generation.credits_used = 0
    generation.tokens_used = 0
    generation.result_json = serialize_model_result_for_storage(result)
    try:
        db.commit()
    except SQLAlchemyError as error:
        db.rollback()
        reset_generation_usage_rollback(reservation)
        raise _internal_error("generation_failure_persistence_failed") from error

    finalize_generation_usage_rollback(reservation)
    if isinstance(result, ErrorResult):
        raise ModelExecutionError(reason=result.reason, message=result.message)

    return GenerationResponse(
        generation_id=generation_id,
        status="failed",
        chatbot_type=generation.chatbot_type,
        result=result,
        usage=GenerationUsage(plan=generation.plan, credits_used=0),
    )


async def generate(
    db: Session,
    user: User,
    request: GenerateRequest,
    idempotency_key: str,
    chatbot_client: ChatbotClient,
    *,
    now,
    free_limit: int,
    model_timeout_seconds: int,
) -> GenerationResponse:
    """D4 생성 요청의 idempotency, reservation, model, persistence를 조율합니다."""
    normalized_key = _normalize_idempotency_key(idempotency_key)
    request_hash = hash_generate_request(request)

    existing = _find_existing_generation(db, user.id, normalized_key)
    if existing is not None:
        return replay_existing_generation(existing, request)

    model_request = build_model_request(db, user, request)

    try:
        reservation = reserve_generation_usage(
            db,
            user.id,
            request.chatbot_type,
            now,
            free_limit,
            request.max_accepted_credits,
        )
        generation = Generation(
            user_id=user.id,
            source_gen_id=request.source_gen_id,
            chatbot_type=request.chatbot_type,
            idempotency_key=normalized_key,
            request_hash=request_hash,
            question=request.question,
            platform=request.platform,
            plan=reservation.plan,
            credits_used=reservation.credits_used,
            status="pending",
        )
        db.add(generation)
        db.flush()
        generation_id = generation.id
        generation.status = "generating"
        db.commit()
    except IntegrityError as error:
        db.rollback()
        existing = _find_existing_generation(db, user.id, normalized_key)
        if existing is None:
            raise _internal_error("generation_idempotency_race_unresolved") from error
        return replay_existing_generation(existing, request)
    except Exception:
        db.rollback()
        raise

    try:
        raw_result = await asyncio.wait_for(
            chatbot_client.generate(model_request),
            timeout=model_timeout_seconds,
        )
        result = MODEL_RESULT_ADAPTER.validate_python(
            raw_result,
            chatbot_type=request.chatbot_type,
        )
    except TimeoutError:
        return _handle_failed_result(
            db,
            user,
            generation_id,
            reservation,
            _failed_error_result("timeout", "model_request_timeout"),
            now=now,
        )
    except (ValidationError, ValueError):
        return _handle_failed_result(
            db,
            user,
            generation_id,
            reservation,
            _failed_error_result("unknown", "model_result_validation_failed"),
            now=now,
        )
    except Exception:
        return _handle_failed_result(
            db,
            user,
            generation_id,
            reservation,
            _failed_error_result("unknown", "model_execution_failed"),
            now=now,
        )

    if isinstance(result, (BlockedResult, ErrorResult)):
        return _handle_failed_result(
            db,
            user,
            generation_id,
            reservation,
            result,
            now=now,
        )

    generation = _load_generating_generation(db, generation_id, user.id)
    generation.result_json = serialize_model_result_for_storage(result)
    generation.title = result.title
    generation.tokens_used = result.tokens_used
    generation.status = "done"
    try:
        db.commit()
    except SQLAlchemyError as error:
        db.rollback()
        raise _internal_error("generation_success_persistence_failed") from error

    settle_generation_usage(reservation)
    return GenerationResponse(
        generation_id=generation_id,
        status="done",
        chatbot_type=request.chatbot_type,
        result=result,
        usage=GenerationUsage(
            plan=reservation.plan,
            credits_used=reservation.credits_used,
        ),
    )
