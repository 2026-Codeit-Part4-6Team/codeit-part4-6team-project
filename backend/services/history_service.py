import json

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models import Generation, User
from backend.schemas import (
    MODEL_RESULT_ADAPTER,
    BasicModelResult,
    BlockedResult,
    ConsultantModelResult,
    ErrorResult,
    GenerationDetailResponse,
    GenerationListItem,
    PublicGenerationResult,
)
from backend.services.generation_service import GenerationDataInvariantError


class GenerationHistoryNotFound(Exception):
    """요청 사용자가 소유한 생성 이력을 찾을 수 없습니다."""


def _list_item(generation: Generation) -> GenerationListItem:
    return GenerationListItem(
        id=generation.id,
        chatbot_type=generation.chatbot_type,
        title=generation.title,
        question=generation.question,
        platform=generation.platform,
        plan=generation.plan,
        credits_used=generation.credits_used,
        tokens_used=generation.tokens_used,
        status=generation.status,
        created_at=generation.created_at,
    )


def list_generations(db: Session, user: User) -> list[GenerationListItem]:
    """현재 사용자의 생성 이력을 newest-first로 반환합니다."""
    rows = db.scalars(
        select(Generation)
        .where(Generation.user_id == user.id)
        .order_by(Generation.created_at.desc(), Generation.id.desc())
    ).all()
    return [_list_item(row) for row in rows]


def _public_history_result(
    generation: Generation,
) -> PublicGenerationResult | None:
    if generation.result_json is None:
        return None
    if generation.status not in {"done", "published", "failed"}:
        return None

    try:
        payload = json.loads(generation.result_json)
        if not isinstance(payload, dict):
            raise TypeError("stored result must be an object")

        if generation.status in {"done", "published"}:
            result = MODEL_RESULT_ADAPTER.validate_python(
                payload,
                chatbot_type=generation.chatbot_type,
            )
            if not isinstance(result, (BasicModelResult, ConsultantModelResult)):
                raise ValueError("completed generation must store a success result")
            return result

        if payload.get("status") == "blocked":
            return BlockedResult.model_validate(payload)
        if payload.get("status") == "error":
            ErrorResult.model_validate(payload)
            return None
        raise ValueError("failed generation must store blocked or error metadata")
    except (json.JSONDecodeError, TypeError, ValueError, ValidationError) as error:
        raise GenerationDataInvariantError(
            "저장된 생성 이력 결과가 Public 계약을 위반합니다."
        ) from error


def get_generation_detail(
    db: Session,
    user: User,
    generation_id: int,
) -> GenerationDetailResponse:
    """소유권을 확인하고 내부 replay 키를 제외한 상세를 반환합니다."""
    generation = db.scalar(
        select(Generation).where(
            Generation.id == generation_id,
            Generation.user_id == user.id,
        )
    )
    if generation is None:
        raise GenerationHistoryNotFound(generation_id)

    item = _list_item(generation)
    return GenerationDetailResponse(
        **item.model_dump(),
        source_gen_id=generation.source_gen_id,
        result=_public_history_result(generation),
        copy_content=generation.copy_content,
        image_b64=(generation.image_b64 if generation.status == "published" else None),
        selected_proposal_index=generation.selected_proposal_index,
        hitl_approved=generation.hitl_approved,
    )
