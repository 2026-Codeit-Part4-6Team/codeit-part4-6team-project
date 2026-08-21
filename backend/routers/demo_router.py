from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.auth import get_current_user
from backend.config import settings
from backend.database import get_db
from backend.models import User
from backend.schemas import DemoTestStateRequest, UserResponse
from backend.services.auth_service import build_user_response
from backend.services.usage_service import next_seoul_midnight_utc

router = APIRouter(prefix="/demo", tags=["demo"])


@router.post("/test-state", response_model=UserResponse)
def update_test_state(
    body: DemoTestStateRequest,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> UserResponse:
    """활성화된 시연 환경에서 관리자 자신의 과금 상태만 변경합니다."""
    if not settings.demo_test_tools_enabled:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    if not user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    if body.daily_free_used > settings.daily_free_limit:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "code": "daily_free_used_exceeds_limit",
                "message": "무료 사용량은 일일 한도를 초과할 수 없습니다.",
            },
        )

    now = datetime.now(UTC)
    user.credits = body.credits
    user.daily_free_used = body.daily_free_used
    user.daily_free_reset_at = next_seoul_midnight_utc(now)
    db.commit()
    db.refresh(user)
    return build_user_response(
        user,
        now=now,
        daily_free_limit=settings.daily_free_limit,
    )
