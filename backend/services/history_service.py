import json
from math import ceil

from pydantic import ValidationError
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from backend.models import Generation, User
from backend.schemas import (
    MODEL_RESULT_ADAPTER,
    BasicModelResult,
    BlockedResult,
    ConsultantModelResult,
    ErrorResult,
    GenerationDetailResponse,
    GenerationHistoryResponse,
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
    rows = db.execute(
        select(
            Generation.id,
            Generation.chatbot_type,
            Generation.title,
            Generation.question,
            Generation.platform,
            Generation.plan,
            Generation.credits_used,
            Generation.tokens_used,
            Generation.status,
            Generation.created_at,
        )
        .where(Generation.user_id == user.id)
        .order_by(Generation.created_at.desc(), Generation.id.desc())
    ).mappings()
    return [GenerationListItem.model_validate(row) for row in rows]


def list_generations_page(
    db: Session,
    user: User,
    *,
    query: str = "",
    page: int = 1,
    page_size: int = 10,
) -> GenerationHistoryResponse:
    """현재 사용자의 이력을 검색하고 페이지 단위로 반환합니다."""
    if page < 1:
        raise ValueError("page는 1 이상이어야 합니다.")
    if not 1 <= page_size <= 50:
        raise ValueError("page_size는 1~50이어야 합니다.")

    normalized_query = query.strip()[:200]
    filters = [Generation.user_id == user.id]
    if normalized_query:
        pattern = f"%{normalized_query}%"
        filters.append(
            or_(
                func.lower(Generation.title).like(func.lower(pattern)),
                func.lower(Generation.question).like(func.lower(pattern)),
            )
        )

    total = db.scalar(select(func.count(Generation.id)).where(*filters)) or 0
    offset = (page - 1) * page_size
    rows = db.execute(
        select(
            Generation.id,
            Generation.chatbot_type,
            Generation.title,
            Generation.question,
            Generation.platform,
            Generation.plan,
            Generation.credits_used,
            Generation.tokens_used,
            Generation.status,
            Generation.created_at,
        )
        .where(*filters)
        .order_by(Generation.created_at.desc(), Generation.id.desc())
        .offset(offset)
        .limit(page_size)
    ).mappings()

    return GenerationHistoryResponse(
        items=[GenerationListItem.model_validate(row) for row in rows],
        page=page,
        page_size=page_size,
        total=total,
        total_pages=ceil(total / page_size) if total else 0,
    )


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
