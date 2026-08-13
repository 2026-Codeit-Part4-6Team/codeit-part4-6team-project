import hashlib
import json
from typing import Literal

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

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
    address = road_address if road_address is not None and road_address.strip() else user.address
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
