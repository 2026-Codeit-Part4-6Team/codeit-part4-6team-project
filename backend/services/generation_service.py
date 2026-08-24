import asyncio
import base64
import binascii
import hashlib
import json
from datetime import datetime, timedelta
from typing import Literal
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy import case, select, update
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from backend.clients.chatbot_client import ChatbotClient
from backend.models import Generation, User
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
    PublishRequest,
    PublishResponse,
    StoreContext,
)
from backend.services.credit_service import (
    apply_generation_usage_rollback,
    finalize_generation_usage_rollback,
    reserve_generation_usage,
    reset_generation_usage_rollback,
    settle_generation_usage,
)
from backend.services.usage_service import as_utc, next_seoul_midnight_utc


class IdempotencyConflict(Exception):
    """같은 Idempotency-Key가 다른 요청 body에 이미 사용되었습니다."""


class SourceGenerationNotFound(Exception):
    """요청 사용자가 소유한 source generation을 찾을 수 없습니다."""


class SourceGenerationConflict(Exception):
    """source generation의 타입 또는 상태가 현재 요청과 호환되지 않습니다."""


class GenerationDataInvariantError(Exception):
    """DB에 저장된 생성 데이터가 서비스 불변조건을 위반합니다."""


class StoreContextValidationError(Exception):
    """서버 소유 사용자/가게 정보로 StoreContext를 구성할 수 없습니다."""


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


class ApprovedImageInvalid(Exception):
    """승인 이미지가 허용된 인코딩 또는 이미지 형식이 아닙니다."""


class ApprovedImageTooLarge(Exception):
    """디코딩한 승인 이미지가 서비스 허용 크기를 초과했습니다."""


class PublishNotFound(Exception):
    """요청 사용자가 소유한 생성 결과를 찾을 수 없습니다."""


class PublishStateConflict(Exception):
    """생성 결과가 게시 승인을 받을 수 없는 상태입니다."""


class PublishTypeConflict(Exception):
    """Basic 생성 결과만 게시 승인할 수 있습니다."""


class PublishProposalInvalid(Exception):
    """저장된 Basic 결과 또는 선택 슬롯이 게시 계약을 위반합니다."""


class PublishPersistenceError(Exception):
    """게시 승인 저장 중 DB 기술 실패가 발생했습니다."""


class PublishedProposalConflict(Exception):
    """이미 다른 제안으로 게시 승인이 완료되었습니다."""


def _detected_image_mime(data: bytes) -> str | None:
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return None


def canonicalize_approved_image(
    image_b64: str | None,
    *,
    max_image_bytes: int,
) -> str | None:
    """허용된 이미지 바이트를 검증해 canonical data URI로 변환합니다."""
    if image_b64 is None:
        return None

    declared_mime: str | None = None
    encoded = image_b64
    if image_b64.startswith("data:"):
        header, separator, encoded = image_b64.partition(",")
        if not separator or not header.endswith(";base64"):
            raise ApprovedImageInvalid("이미지는 base64 data URI여야 합니다.")
        declared_mime = header[5:-7]
        if declared_mime not in {"image/png", "image/jpeg", "image/webp"}:
            raise ApprovedImageInvalid("PNG, JPEG, WebP 이미지만 승인할 수 있습니다.")

    try:
        data = base64.b64decode(encoded, validate=True)
    except (ValueError, binascii.Error) as error:
        raise ApprovedImageInvalid("이미지 base64 인코딩이 올바르지 않습니다.") from error

    if len(data) > max_image_bytes:
        raise ApprovedImageTooLarge("승인 이미지가 허용 크기를 초과했습니다.")

    detected_mime = _detected_image_mime(data)
    if detected_mime is None or (
        declared_mime is not None and declared_mime != detected_mime
    ):
        raise ApprovedImageInvalid("이미지 MIME과 실제 바이트 형식이 올바르지 않습니다.")

    canonical = base64.b64encode(data).decode("ascii")
    return f"data:{detected_mime};base64,{canonical}"


def _published_response(
    generation: Generation,
    proposal_index: Literal[0, 1, 2],
) -> PublishResponse:
    if generation.selected_proposal_index != proposal_index:
        raise PublishedProposalConflict("이미 다른 제안으로 게시되었습니다.")
    if not generation.hitl_approved:
        raise PublishStateConflict("게시 상태의 승인 정보가 올바르지 않습니다.")
    return PublishResponse(
        generation_id=generation.id,
        status="published",
        hitl_approved=True,
        proposal_index=proposal_index,
    )


async def publish_generation(
    db: Session,
    user: User,
    generation_id: int,
    request: PublishRequest,
    *,
    max_image_bytes: int,
) -> PublishResponse:
    """Basic 제안 한 슬롯을 done→published CAS로 승인합니다."""
    generation = db.scalar(
        select(Generation).where(
            Generation.id == generation_id,
            Generation.user_id == user.id,
        )
    )
    if generation is None:
        db.rollback()
        raise PublishNotFound(generation_id)
    if generation.chatbot_type != "basic":
        db.rollback()
        raise PublishTypeConflict("Basic 생성 결과만 게시할 수 있습니다.")
    if generation.status == "published":
        return _published_response(generation, request.proposal_index)
    if generation.status != "done":
        db.rollback()
        raise PublishStateConflict("완료된 생성 결과만 게시할 수 있습니다.")
    if generation.result_json is None:
        db.rollback()
        raise PublishProposalInvalid("저장된 Basic 결과가 없습니다.")

    try:
        basic_result = BasicModelResult.model_validate_json(generation.result_json)
        selected = basic_result.proposals[request.proposal_index]
    except (ValidationError, ValueError, TypeError, IndexError) as error:
        db.rollback()
        raise PublishProposalInvalid("저장된 Basic 결과가 올바르지 않습니다.") from error
    if selected.copy is None or not selected.copy.strip():
        db.rollback()
        raise PublishProposalInvalid("선택한 제안에 게시할 문구가 없습니다.")

    try:
        canonical_image = canonicalize_approved_image(
            request.image_b64,
            max_image_bytes=max_image_bytes,
        )
    except (ApprovedImageInvalid, ApprovedImageTooLarge):
        db.rollback()
        raise

    statement = (
        update(Generation)
        .where(
            Generation.id == generation_id,
            Generation.user_id == user.id,
            Generation.status == "done",
        )
        .values(
            copy_content=selected.copy,
            image_b64=canonical_image,
            selected_proposal_index=request.proposal_index,
            hitl_approved=True,
            status="published",
        )
    )
    try:
        result = db.execute(statement)
        if result.rowcount == 1:
            db.commit()
            return PublishResponse(
                generation_id=generation_id,
                status="published",
                hitl_approved=True,
                proposal_index=request.proposal_index,
            )
        db.rollback()
    except SQLAlchemyError as error:
        db.rollback()
        raise PublishPersistenceError("게시 승인 저장에 실패했습니다.") from error

    current = db.scalar(
        select(Generation).where(
            Generation.id == generation_id,
            Generation.user_id == user.id,
        )
    )
    if current is None:
        raise PublishNotFound(generation_id)
    if current.status == "published":
        return _published_response(current, request.proposal_index)
    raise PublishStateConflict("생성 상태가 변경되어 게시하지 못했습니다.")


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
        raise StoreContextValidationError(f"{field_name} 값이 필요합니다.")
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
        raise StoreContextValidationError("가게 좌표가 필요합니다.")

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
        raise StoreContextValidationError(
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


def recover_stale_generating(
    db: Session,
    generation: Generation,
    user: User,
    *,
    now: datetime,
    stale_recovery_seconds: int,
) -> bool:
    """same-key retry에서 stale generating reservation을 정확히 한 번 복구합니다."""
    if stale_recovery_seconds <= 0:
        raise ValueError("stale_recovery_seconds는 양수여야 합니다.")
    if generation.status != "generating":
        return False
    if generation.created_at is None:
        raise GenerationDataInvariantError("generation.created_at이 필요합니다.")

    normalized_now = as_utc(now)
    started_at = as_utc(generation.created_at)
    stale_at = started_at + timedelta(seconds=stale_recovery_seconds)
    if normalized_now < stale_at:
        return False

    reserved_credits = generation.credits_used
    plan = generation.plan
    safe_error = _failed_error_result("unknown", "stale_generation_recovered")
    claim = db.execute(
        update(Generation)
        .where(
            Generation.id == generation.id,
            Generation.user_id == user.id,
            Generation.status == "generating",
        )
        .values(
            status="failed",
            credits_used=0,
            tokens_used=0,
            result_json=serialize_model_result_for_storage(safe_error),
        )
        .execution_options(synchronize_session=False)
    )
    if claim.rowcount != 1:
        db.rollback()
        return False

    if plan == "paid":
        db.execute(
            update(User)
            .where(User.id == user.id)
            .values(credits=User.credits + reserved_credits)
            .execution_options(synchronize_session=False)
        )
    elif plan == "free":
        reserved_period_reset_at = next_seoul_midnight_utc(started_at)
        current_reset_at = db.scalar(
            select(User.daily_free_reset_at).where(User.id == user.id)
        )
        if (
            current_reset_at is not None
            and as_utc(current_reset_at) == reserved_period_reset_at
        ):
            db.execute(
                update(User)
                .where(
                    User.id == user.id,
                    User.daily_free_reset_at == current_reset_at,
                )
                .values(
                    daily_free_used=case(
                        (User.daily_free_used > 0, User.daily_free_used - 1),
                        else_=0,
                    )
                )
                .execution_options(synchronize_session=False)
            )
    else:
        db.rollback()
        raise GenerationDataInvariantError("generation plan이 올바르지 않습니다.")

    try:
        db.commit()
    except SQLAlchemyError as error:
        db.rollback()
        raise _internal_error("stale_generation_recovery_failed") from error
    return True


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
    stale_recovery_seconds: int = 120,
) -> GenerationResponse:
    """D4 생성 요청의 idempotency, reservation, model, persistence를 조율합니다."""
    normalized_key = _normalize_idempotency_key(idempotency_key)
    request_hash = hash_generate_request(request)

    existing = _find_existing_generation(db, user.id, normalized_key)
    if existing is not None:
        if existing.request_hash != request_hash:
            raise IdempotencyConflict(
                "같은 Idempotency-Key가 다른 요청에 사용되었습니다."
            )
        if existing.status == "generating":
            recovered = recover_stale_generating(
                db,
                existing,
                user,
                now=now,
                stale_recovery_seconds=stale_recovery_seconds,
            )
            if recovered:
                raise _internal_error("stale_generation_recovered")
            existing = _find_existing_generation(db, user.id, normalized_key)
            if existing is None:
                raise GenerationDataInvariantError(
                    "idempotent generation row가 사라졌습니다."
                )
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
    # The model client is an external trust boundary. Any unexpected provider
    # failure must follow the same reservation-compensation path.
    except Exception:  # noqa: BLE001
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
