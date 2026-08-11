from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from backend.models import User
from backend.time_utils import as_utc, next_seoul_midnight_utc


@dataclass(frozen=True)
class UsageReservation:
    """무료 생성 요청이 예약한 사용량입니다."""

    plan: Literal["free"] = "free"
    credits_used: Literal[0] = 0
    free_count_incremented: bool = True


def reset_daily_usage_if_due(user: User, now: datetime) -> bool:
    """리셋 시각이 도래했으면 무료 사용량과 다음 리셋 시각을 갱신합니다."""
    current = as_utc(now)
    reset_at = user.daily_free_reset_at
    if reset_at is not None and as_utc(reset_at) > current:
        return False

    user.daily_free_used = 0
    user.daily_free_reset_at = next_seoul_midnight_utc(current)
    return True


def try_reserve_free_usage(
    user: User, now: datetime, limit: int
) -> UsageReservation | None:
    """무료 사용 가능 시 카운터를 증가시키고 예약 정보를 반환합니다."""
    if limit < 0:
        raise ValueError("무료 사용 한도는 0 이상이어야 합니다.")
    reset_daily_usage_if_due(user, now)
    if user.daily_free_used >= limit:
        return None

    user.daily_free_used += 1
    return UsageReservation()


def rollback_free_usage(user: User, reservation: UsageReservation) -> None:
    """예약에서 증가한 무료 사용량을 0 미만이 되지 않게 복구합니다."""
    if reservation.free_count_incremented:
        user.daily_free_used = max(0, user.daily_free_used - 1)
