from dataclasses import dataclass
from datetime import UTC, datetime, time, timedelta
from typing import Literal
from zoneinfo import ZoneInfo

from sqlalchemy import case, or_, select, update
from sqlalchemy.orm import Session

from backend.models import User

ReservationState = Literal["pending", "settled", "rolled_back"]
SEOUL_TIMEZONE = ZoneInfo("Asia/Seoul")


@dataclass
class UsageReservation:
    """무료 생성 1회의 DB 예약 상태."""

    plan: Literal["free"]
    credits_used: Literal[0]
    period_reset_at: datetime
    incremented: bool
    state: ReservationState = "pending"
    compensation_applied: bool = False


def as_utc(value: datetime) -> datetime:
    """aware datetime은 UTC로, SQLite naive datetime은 UTC로 간주합니다."""
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def next_seoul_midnight_utc(now: datetime) -> datetime:
    """현재 시각 이후의 Asia/Seoul 자정을 UTC aware datetime으로 반환합니다."""
    current = as_utc(now)
    local_date = current.astimezone(SEOUL_TIMEZONE).date() + timedelta(days=1)
    local_midnight = datetime.combine(local_date, time.min, tzinfo=SEOUL_TIMEZONE)
    return local_midnight.astimezone(UTC)


def effective_daily_usage(user: User, now: datetime) -> tuple[int, datetime]:
    """ORM을 변경하지 않고 현재 period의 무료 사용량과 reset 시각을 계산합니다."""
    normalized_now = as_utc(now)
    normalized_reset_at = (
        None if user.daily_free_reset_at is None else as_utc(user.daily_free_reset_at)
    )
    if normalized_reset_at is None or normalized_now >= normalized_reset_at:
        return 0, next_seoul_midnight_utc(normalized_now)
    return user.daily_free_used, normalized_reset_at


def _bind_utc(db: Session, value: datetime) -> datetime:
    """SQLite에는 UTC naive, timezone 지원 DB에는 UTC aware 값을 bind합니다."""
    normalized = as_utc(value)
    bind = db.get_bind()
    if bind.dialect.name == "sqlite":
        return normalized.replace(tzinfo=None)
    return normalized


def reset_daily_usage_if_due(db: Session, user_id: int, now: datetime) -> bool:
    """리셋 시각이 지난 사용자 row만 조건부 UPDATE로 새 period를 시작합니다."""
    normalized_now = as_utc(now)
    next_reset_at = next_seoul_midnight_utc(normalized_now)
    result = db.execute(
        update(User)
        .where(
            User.id == user_id,
            or_(
                User.daily_free_reset_at.is_(None),
                User.daily_free_reset_at <= _bind_utc(db, normalized_now),
            ),
        )
        .values(
            daily_free_used=0,
            daily_free_reset_at=_bind_utc(db, next_reset_at),
        )
        .execution_options(synchronize_session=False)
    )
    return result.rowcount == 1


def try_reserve_free_usage(
    db: Session,
    user_id: int,
    now: datetime,
    limit: int,
) -> UsageReservation | None:
    """무료 슬롯을 DB 조건부 UPDATE로 정확히 한 번 예약합니다."""
    if limit < 0:
        raise ValueError("daily free limit은 0 이상이어야 합니다.")
    if limit == 0:
        return None

    reset_daily_usage_if_due(db, user_id, now)

    result = db.execute(
        update(User)
        .where(User.id == user_id, User.daily_free_used < limit)
        .values(daily_free_used=User.daily_free_used + 1)
        .execution_options(synchronize_session=False)
    )
    if result.rowcount != 1:
        return None

    period_reset_at = db.scalar(
        select(User.daily_free_reset_at).where(User.id == user_id)
    )
    if period_reset_at is None:
        raise RuntimeError("무료 사용량 예약 후 reset 시각이 존재해야 합니다.")

    return UsageReservation(
        plan="free",
        credits_used=0,
        period_reset_at=as_utc(period_reset_at),
        incremented=True,
    )


def apply_free_usage_rollback(
    db: Session,
    user_id: int,
    reservation: UsageReservation,
    now: datetime,
) -> None:
    """현재 transaction에 무료 사용량 보상 mutation을 최대 1회 적용합니다."""
    if reservation.state != "pending" or reservation.compensation_applied:
        return

    as_utc(now)
    if reservation.incremented:
        db.execute(
            update(User)
            .where(
                User.id == user_id,
                User.daily_free_reset_at
                == _bind_utc(db, reservation.period_reset_at),
            )
            .values(
                daily_free_used=case(
                    (User.daily_free_used > 0, User.daily_free_used - 1),
                    else_=0,
                )
            )
            .execution_options(synchronize_session=False)
        )
    reservation.compensation_applied = True


def reset_free_usage_rollback(reservation: UsageReservation) -> None:
    """보상 transaction rollback 뒤 transient marker를 재시도 가능 상태로 되돌립니다."""
    if reservation.state == "pending":
        reservation.compensation_applied = False


def finalize_free_usage_rollback(reservation: UsageReservation) -> None:
    """보상 DB commit 성공 뒤 무료 Reservation을 rolled_back으로 확정합니다."""
    if reservation.state == "pending" and reservation.compensation_applied:
        reservation.state = "rolled_back"
        reservation.compensation_applied = False


def settle_free_usage(reservation: UsageReservation) -> None:
    """성공 DB commit 뒤 무료 Reservation을 settled로 확정합니다."""
    if reservation.state == "pending" and not reservation.compensation_applied:
        reservation.state = "settled"
