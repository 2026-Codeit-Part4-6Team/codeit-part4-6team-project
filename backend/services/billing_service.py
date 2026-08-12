from dataclasses import dataclass
from datetime import datetime

from backend.config import settings
from backend.models import User
from backend.schemas import ChatbotType
from backend.services.credit_service import (
    CreditReservation,
    InsufficientCredits,
    credit_cost_for,
    reserve_credits,
    rollback_credits,
)
from backend.services.usage_service import (
    UsageReservation,
    rollback_free_usage,
    try_reserve_free_usage,
)
from backend.time_utils import as_utc


@dataclass(frozen=True)
class BillingEstimate:
    """생성 전 과금 예상값입니다."""

    is_free: bool
    free_remaining: int
    estimated_credits: int
    current_credits: int
    credits_after: int
    requires_confirmation: bool


BillingReservation = UsageReservation | CreditReservation


def _virtual_free_remaining(user: User, now: datetime, free_limit: int) -> int:
    """Estimate용으로 리셋을 적용한 가상의 무료 잔여를 계산합니다."""
    if free_limit < 0:
        raise ValueError("무료 사용 한도는 0 이상이어야 합니다.")

    current = as_utc(now)
    reset_at = user.daily_free_reset_at
    used = user.daily_free_used
    if reset_at is None or as_utc(reset_at) <= current:
        used = 0
    return max(0, free_limit - used)


def estimate_generation(
    user: User,
    chatbot_type: ChatbotType,
    now: datetime,
    *,
    free_limit: int,
) -> BillingEstimate:
    """사용자 상태를 변경하지 않고 무료·유료 생성 비용을 예상합니다."""
    free_remaining = _virtual_free_remaining(user, now, free_limit)
    if free_remaining > 0:
        return BillingEstimate(
            is_free=True,
            free_remaining=free_remaining - 1,
            estimated_credits=0,
            current_credits=user.credits,
            credits_after=user.credits,
            requires_confirmation=False,
        )

    cost = credit_cost_for(chatbot_type)
    if user.credits < cost:
        raise InsufficientCredits(required=cost, available=user.credits)
    return BillingEstimate(
        is_free=False,
        free_remaining=0,
        estimated_credits=cost,
        current_credits=user.credits,
        credits_after=user.credits - cost,
        requires_confirmation=cost > 0,
    )


def reserve_generation_usage(
    user: User,
    chatbot_type: ChatbotType,
    now: datetime,
    *,
    free_limit: int | None = None,
) -> BillingReservation:
    """무료를 우선 예약하고, 소진 시 챗봇별 Credit을 예약합니다."""
    limit = settings.daily_free_limit if free_limit is None else free_limit
    free_reservation = try_reserve_free_usage(user, now, limit)
    if free_reservation is not None:
        return free_reservation
    return reserve_credits(user, chatbot_type)


def rollback_generation_usage(user: User, reservation: BillingReservation) -> None:
    """무료 또는 유료 예약을 공통 경계에서 rollback합니다."""
    if reservation.plan == "free":
        rollback_free_usage(user, reservation)
    else:
        rollback_credits(user, reservation)
