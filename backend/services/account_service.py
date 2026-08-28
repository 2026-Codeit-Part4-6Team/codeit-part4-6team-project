from datetime import datetime

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from backend.models import Generation, User
from backend.schemas import UserSummaryResponse
from backend.services.usage_service import effective_daily_usage


def build_user_summary(
    db: Session,
    user: User,
    *,
    now: datetime,
    daily_free_limit: int,
) -> UserSummaryResponse:
    """DB mutation 없이 현재 사용자의 사용량과 생성 이력을 집계합니다."""
    total, published = db.execute(
        select(
            func.count(Generation.id),
            func.count(case((Generation.status == "published", 1))),
        ).where(Generation.user_id == user.id)
    ).one()
    used, _reset_at = effective_daily_usage(user, now)
    return UserSummaryResponse(
        credits=user.credits,
        daily_free_remaining=max(0, daily_free_limit - used),
        total_generations=total,
        published_generations=published,
    )
