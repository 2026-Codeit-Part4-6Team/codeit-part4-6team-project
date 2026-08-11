from datetime import UTC, datetime

from backend.models import User
from backend.services.usage_service import (
    UsageReservation,
    reset_daily_usage_if_due,
    rollback_free_usage,
    try_reserve_free_usage,
)
from backend.time_utils import next_seoul_midnight_utc


def make_user(*, used: int, reset_at: datetime | None) -> User:
    """사용량 테스트용 사용자를 생성합니다."""
    return User(
        username="owner",
        password_hash="hash",
        daily_free_used=used,
        daily_free_reset_at=reset_at,
    )


def test_next_seoul_midnight_utc_handles_korean_date_boundary():
    """UTC 오후에도 다음 한국 자정을 정확히 계산합니다."""
    now = datetime(2026, 8, 11, 16, 0, tzinfo=UTC)

    assert next_seoul_midnight_utc(now) == datetime(2026, 8, 12, 15, 0, tzinfo=UTC)


def test_reset_daily_usage_when_reset_time_has_arrived():
    """리셋 시각이 지났으면 카운터를 비우고 다음 한국 자정을 예약합니다."""
    now = datetime(2026, 8, 11, 16, 0, tzinfo=UTC)
    user = make_user(used=7, reset_at=datetime(2026, 8, 11, 15, 0, tzinfo=UTC))

    changed = reset_daily_usage_if_due(user, now)

    assert changed is True
    assert user.daily_free_used == 0
    assert user.daily_free_reset_at == datetime(2026, 8, 12, 15, 0, tzinfo=UTC)


def test_reset_daily_usage_accepts_naive_sqlite_datetime_as_utc():
    """SQLite가 반환한 naive 시각도 UTC로 해석해 리셋합니다."""
    now = datetime(2026, 8, 11, 16, 0, tzinfo=UTC)
    user = make_user(used=4, reset_at=datetime(2026, 8, 11, 15, 0))  # noqa: DTZ001

    assert reset_daily_usage_if_due(user, now) is True
    assert user.daily_free_used == 0


def test_reset_daily_usage_leaves_counter_before_reset_time():
    """리셋 시각 전에는 사용자 상태를 변경하지 않습니다."""
    now = datetime(2026, 8, 11, 14, 0, tzinfo=UTC)
    reset_at = datetime(2026, 8, 11, 15, 0, tzinfo=UTC)
    user = make_user(used=3, reset_at=reset_at)

    changed = reset_daily_usage_if_due(user, now)

    assert changed is False
    assert user.daily_free_used == 3
    assert user.daily_free_reset_at == reset_at


def test_free_usage_reservation_increments_until_limit():
    """무료 한도까지 예약하고 소진 뒤에는 예약하지 않습니다."""
    now = datetime(2026, 8, 11, 14, 0, tzinfo=UTC)
    user = make_user(
        used=9,
        reset_at=datetime(2026, 8, 11, 15, 0, tzinfo=UTC),
    )

    reservation = try_reserve_free_usage(user, now, limit=10)
    exhausted = try_reserve_free_usage(user, now, limit=10)

    assert reservation == UsageReservation()
    assert user.daily_free_used == 10
    assert exhausted is None


def test_free_usage_rollback_never_goes_below_zero():
    """무료 예약 복구는 증가분만 되돌리고 카운터를 음수로 만들지 않습니다."""
    user = make_user(used=1, reset_at=None)
    rollback_free_usage(user, UsageReservation())
    assert user.daily_free_used == 0

    rollback_free_usage(user, UsageReservation())
    assert user.daily_free_used == 0

    rollback_free_usage(user, UsageReservation(free_count_incremented=False))
    assert user.daily_free_used == 0
