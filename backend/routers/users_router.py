from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.auth import get_current_user
from backend.config import settings
from backend.database import get_db
from backend.models import User
from backend.schemas import UserResponse, UserSummaryResponse
from backend.services.account_service import build_user_summary
from backend.services.auth_service import build_user_response

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserResponse)
def read_me(user: Annotated[User, Depends(get_current_user)]) -> UserResponse:
    """현재 로그인한 사용자 정보를 반환합니다."""
    return build_user_response(
        user, now=datetime.now(UTC), daily_free_limit=settings.daily_free_limit
    )


@router.get("/me/summary", response_model=UserSummaryResponse)
def read_summary(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> UserSummaryResponse:
    """현재 사용자의 Credit·무료 횟수·생성 이력을 서버에서 계산합니다."""
    return build_user_summary(
        db,
        user,
        now=datetime.now(UTC),
        daily_free_limit=settings.daily_free_limit,
    )
