from datetime import UTC, datetime

import pytest

from backend.models import User
from backend.services.billing_service import (
    estimate_generation,
    reserve_generation_usage,
    rollback_generation_usage,
)
from backend.services.credit_service import InsufficientCredits
from backend.services.usage_service import UsageReservation


def make_user(*, used: int, credits: int, reset_at: datetime) -> User:
    return User(
        username="owner",
        password_hash="hash",
        daily_free_used=used,
        credits=credits,
        daily_free_reset_at=reset_at,
    )


def test_estimate_is_side_effect_free_for_free_generation():
    """무료 예상 조회는 사용자 상태를 변경하지 않습니다."""
    reset_at = datetime(2026, 8, 12, 15, 0, tzinfo=UTC)
    user = make_user(used=3, credits=40, reset_at=reset_at)

    result = estimate_generation(
        user,
        "basic",
        datetime(2026, 8, 11, 16, 0, tzinfo=UTC),
        free_limit=10,
    )

    assert result.is_free is True
    assert result.free_remaining == 6
    assert result.estimated_credits == 0
    assert result.credits_after == 40
    assert (user.daily_free_used, user.credits, user.daily_free_reset_at) == (3, 40, reset_at)


def test_estimate_uses_paid_cost_after_free_quota_without_mutation():
    """무료 소진 후 예상 조회는 챗봇별 비용만 계산합니다."""
    reset_at = datetime(2026, 8, 12, 15, 0, tzinfo=UTC)
    user = make_user(used=10, credits=60, reset_at=reset_at)

    result = estimate_generation(
        user,
        "consultant",
        datetime(2026, 8, 11, 16, 0, tzinfo=UTC),
        free_limit=10,
    )

    assert result.is_free is False
    assert result.free_remaining == 0
    assert result.estimated_credits == 50
    assert result.credits_after == 10
    assert result.requires_confirmation is True
    assert user.credits == 60


def test_estimate_rejects_insufficient_paid_balance_without_mutation():
    """유료 예상 금액보다 잔액이 적으면 상태를 바꾸지 않습니다."""
    user = make_user(
        used=10,
        credits=49,
        reset_at=datetime(2026, 8, 12, 15, 0, tzinfo=UTC),
    )

    with pytest.raises(InsufficientCredits):
        estimate_generation(
            user,
            "consultant",
            datetime(2026, 8, 11, 16, 0, tzinfo=UTC),
            free_limit=10,
        )

    assert (user.daily_free_used, user.credits) == (10, 49)


def test_reservation_and_rollback_share_one_billing_boundary():
    """무료 예약은 공통 rollback으로 증가분만 복구합니다."""
    user = make_user(
        used=9,
        credits=0,
        reset_at=datetime(2026, 8, 12, 15, 0, tzinfo=UTC),
    )
    now = datetime(2026, 8, 11, 16, 0, tzinfo=UTC)

    reservation = reserve_generation_usage(user, "basic", now, free_limit=10)
    rollback_generation_usage(user, reservation)

    assert isinstance(reservation, UsageReservation)
    assert user.daily_free_used == 9
