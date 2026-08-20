from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from backend.auth import get_current_user
from backend.config import settings
from backend.models import User
from backend.schemas import (
    GenerateEstimateRequest,
    GenerateEstimateResponse,
    PreviewGenerateRequest,
    PreviewGenerateResponse,
)
from backend.services.credit_service import InsufficientCredits, estimate_generation
from backend.services.generation_service import GenerationService

router = APIRouter(tags=["generation"])
generation_service = GenerationService()


@router.post("/generate", response_model=PreviewGenerateResponse)
def generate(request: PreviewGenerateRequest) -> PreviewGenerateResponse:
    """D4 전까지 유지하는 컨테이너 연결 검증용 Preview 생성 요청."""
    return generation_service.generate(request)


@router.post("/generate/estimate", response_model=GenerateEstimateResponse)
def estimate(
    request: GenerateEstimateRequest,
    user: Annotated[User, Depends(get_current_user)],
) -> GenerateEstimateResponse:
    """모델 호출이나 DB mutation 없이 현재 무료/Credit 예상값을 반환합니다."""
    try:
        estimate_result = estimate_generation(
            user,
            request.chatbot_type,
            datetime.now(UTC),
            settings.daily_free_limit,
        )
    except InsufficientCredits as error:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail={"required": error.required, "current": error.current},
        ) from error
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={"code": "invalid_generation_request", "message": str(error)},
        ) from error

    return GenerateEstimateResponse(
        is_free=estimate_result.is_free,
        free_remaining=estimate_result.free_remaining,
        estimated_credits=estimate_result.estimated_credits,
        current_credits=estimate_result.current_credits,
        credits_after=estimate_result.credits_after,
        requires_confirmation=estimate_result.requires_confirmation,
    )
