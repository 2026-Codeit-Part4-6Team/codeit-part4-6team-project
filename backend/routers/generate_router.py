from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from backend.auth import get_current_user
from backend.config import settings
from backend.database import get_db
from backend.models import User
from backend.schemas import (
    GenerateEstimateRequest,
    GenerateEstimateResponse,
    GenerateRequest,
    GenerationResponse,
)
from backend.services.credit_service import (
    BillingConfirmationRequired,
    InsufficientCredits,
    estimate_generation,
)
from backend.services.generation_service import (
    GenerationDataInvariantError,
    IdempotencyConflict,
    ModelExecutionError,
    SourceGenerationConflict,
    SourceGenerationNotFound,
    StoreContextValidationError,
)
from backend.services.generation_service import (
    generate as generate_generation,
)

router = APIRouter(tags=["generation"])


@router.post("/generate", response_model=GenerationResponse)
async def generate(
    http_request: Request,
    request: GenerateRequest,
    idempotency_key: Annotated[UUID, Header(alias="Idempotency-Key")],
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> GenerationResponse:
    """D4 실제 생성 요청을 Service 오케스트레이션에 위임합니다."""
    try:
        return await generate_generation(
            db,
            user,
            request,
            str(idempotency_key),
            http_request.app.state.chatbot_client,
            now=datetime.now(UTC),
            free_limit=settings.daily_free_limit,
            model_timeout_seconds=settings.model_request_timeout_seconds,
            stale_recovery_seconds=settings.stale_recovery_seconds,
        )
    except InsufficientCredits as error:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail={"required": error.required, "current": error.current},
        ) from error
    except BillingConfirmationRequired as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "reason": "billing_confirmation_required",
                "required": error.required,
                "accepted": error.accepted,
            },
        ) from error
    except IdempotencyConflict as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"reason": "idempotency_conflict"},
        ) from error
    except SourceGenerationNotFound as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"reason": "source_generation_not_found"},
        ) from error
    except SourceGenerationConflict as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"reason": "source_generation_conflict"},
        ) from error
    except StoreContextValidationError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={"reason": "generation_data_invariant"},
        ) from error
    except GenerationDataInvariantError as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"reason": "generation_data_invariant"},
        ) from error
    except ModelExecutionError as error:
        status_by_reason = {
            "rate_limit": status.HTTP_429_TOO_MANY_REQUESTS,
            "provider_error": status.HTTP_502_BAD_GATEWAY,
            "timeout": status.HTTP_504_GATEWAY_TIMEOUT,
            "unknown": status.HTTP_500_INTERNAL_SERVER_ERROR,
        }
        raise HTTPException(
            status_code=status_by_reason[error.reason],
            detail={"reason": error.reason},
        ) from error
    except SQLAlchemyError as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"reason": "internal_error"},
        ) from error


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
