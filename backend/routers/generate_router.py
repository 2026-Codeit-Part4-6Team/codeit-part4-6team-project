from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from backend.auth import get_current_user
from backend.config import settings
from backend.models import User
from backend.schemas import (
    GenerateEstimateResponse,
    GenerateRequest,
    PreviewGenerateRequest,
    PreviewGenerateResponse,
)
from backend.services.billing_service import estimate_generation
from backend.services.credit_service import InsufficientCredits
from backend.services.generation_service import GenerationService

router = APIRouter(tags=["generation"])
generation_service = GenerationService()


@router.post("/generate/estimate", response_model=GenerateEstimateResponse)
def estimate(
    request: GenerateRequest,
    user: Annotated[User, Depends(get_current_user)],
) -> GenerateEstimateResponse:
    """모델 호출과 상태 변경 없이 생성 비용을 예상합니다."""
    try:
        result = estimate_generation(
            user,
            request.chatbot_type,
            datetime.now(UTC),
            free_limit=settings.daily_free_limit,
        )
    except InsufficientCredits as error:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail={
                "code": "insufficient_credits",
                "required": error.required,
                "current": error.available,
            },
        ) from error
    return GenerateEstimateResponse(
        is_free=result.is_free,
        free_remaining=result.free_remaining,
        estimated_credits=result.estimated_credits,
        current_credits=result.current_credits,
        credits_after=result.credits_after,
        requires_confirmation=result.requires_confirmation,
    )


@router.post("/generate", response_model=PreviewGenerateResponse)
def generate(request: PreviewGenerateRequest) -> PreviewGenerateResponse:
    """광고 콘텐츠 생성 요청을 처리합니다."""
    return generation_service.generate(request)
