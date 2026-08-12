from dataclasses import replace

import pytest

from backend.config import settings
from backend.models import User
from backend.services import credit_service
from backend.services.credit_service import (
    CreditReservation,
    InsufficientCredits,
    credit_cost_for,
    reserve_credits,
    rollback_credits,
)


def make_user(credits: int) -> User:
    """크레딧 테스트용 사용자를 생성합니다."""
    return User(username="owner", password_hash="hash", credits=credits)


def test_credit_cost_uses_chatbot_specific_policy():
    """Basic은 10, Consultant는 50 Credit을 사용합니다."""
    assert credit_cost_for("basic") == 10
    assert credit_cost_for("consultant") == 50


def test_credit_cost_rejects_unknown_chatbot_type():
    """계약 밖의 챗봇 종류는 Consultant 비용으로 fallback하지 않습니다."""
    with pytest.raises(ValueError, match="지원하지 않는 챗봇 종류"):
        credit_cost_for("unknown")


@pytest.mark.parametrize(
    ("chatbot_type", "before", "expected_cost"),
    [("basic", 60, 10), ("consultant", 60, 50)],
)
def test_reserve_credits_deducts_exact_cost(chatbot_type, before, expected_cost):
    """챗봇별 비용을 정확히 차감하고 예약 정보를 반환합니다."""
    user = make_user(before)

    reservation = reserve_credits(user, chatbot_type)

    assert reservation == CreditReservation(credits_used=expected_cost)
    assert user.credits == before - expected_cost


def test_reserve_credits_rejects_insufficient_balance_without_mutation():
    """잔액 부족 시 필요한 금액을 알리고 잔액을 변경하지 않습니다."""
    user = make_user(49)

    with pytest.raises(InsufficientCredits) as caught:
        reserve_credits(user, "consultant")

    assert caught.value.required == 50
    assert caught.value.available == 49
    assert user.credits == 49


def test_zero_cost_policy_is_valid(monkeypatch):
    """설정값이 0이면 차감 없이 유료 예약 형식을 반환합니다."""
    monkeypatch.setattr(
        credit_service,
        "settings",
        replace(settings, basic_credit_cost=0),
    )
    user = make_user(0)

    reservation = reserve_credits(user, "basic")

    assert reservation.credits_used == 0
    assert user.credits == 0


def test_rollback_credits_restores_reserved_amount():
    """예약한 크레딧을 사용자 잔액에 정확히 복구합니다."""
    user = make_user(50)
    reservation = reserve_credits(user, "consultant")

    rollback_credits(user, reservation)

    assert user.credits == 50
