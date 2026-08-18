from dataclasses import dataclass
from datetime import datetime
from typing import Literal, TypeAlias

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from backend.config import settings
from backend.models import User
from backend.services.usage_service import (
    UsageReservation,
    apply_free_usage_rollback,
    effective_daily_usage,
    finalize_free_usage_rollback,
    reset_free_usage_rollback,
    settle_free_usage,
    try_reserve_free_usage,
)

ReservationState = Literal["pending", "settled", "rolled_back"]


@dataclass
class CreditReservation:
    """유료 생성 1회의 Credit DB 예약 상태."""

    plan: Literal["paid"]
    credits_used: int
    state: ReservationState = "pending"
    compensation_applied: bool = False


@dataclass(frozen=True)
class GenerationEstimate:
    """DB를 변경하지 않는 생성 전 과금 예상값."""

    is_free: bool
    free_remaining: int
    estimated_credits: int
    current_credits: int
    credits_after: int
    requires_confirmation: bool


class InsufficientCredits(Exception):
    """현재 Credit으로 실제 비용을 지불할 수 없습니다."""

    def __init__(self, *, required: int, current: int) -> None:
        self.required = required
        self.current = current
        super().__init__(f"required={required}, current={current}")


class BillingConfirmationRequired(Exception):
    """실제 비용이 사용자가 승인한 상한보다 큽니다."""

    def __init__(self, *, required: int, accepted: int) -> None:
        self.required = required
        self.accepted = accepted
        super().__init__(f"required={required}, accepted={accepted}")


Reservation: TypeAlias = UsageReservation | CreditReservation


def credit_cost_for(chatbot_type: Literal["basic", "consultant"] | str) -> int:
    """decisions.md와 Settings를 단일 소스로 챗봇별 실제 비용을 반환합니다."""
    if chatbot_type == "basic":
        return settings.basic_credit_cost
    if chatbot_type == "consultant":
        return settings.consultant_credit_cost
    raise ValueError("chatbot_type은 basic 또는 consultant여야 합니다.")


def estimate_generation(
    user: User,
    chatbot_type: str,
    now: datetime,
    free_limit: int,
) -> GenerationEstimate:
    """ORM을 변경하지 않고 현재 시각 기준 무료/유료 예상값을 계산합니다."""
    if free_limit < 0:
        raise ValueError("daily free limit은 0 이상이어야 합니다.")

    cost = credit_cost_for(chatbot_type)
    used, _reset_at = effective_daily_usage(user, now)
    free_remaining = max(0, free_limit - used)
    if free_remaining > 0:
        return GenerationEstimate(
            is_free=True,
            free_remaining=free_remaining,
            estimated_credits=0,
            current_credits=user.credits,
            credits_after=user.credits,
            requires_confirmation=False,
        )

    if user.credits < cost:
        raise InsufficientCredits(required=cost, current=user.credits)

    return GenerationEstimate(
        is_free=False,
        free_remaining=0,
        estimated_credits=cost,
        current_credits=user.credits,
        credits_after=user.credits - cost,
        requires_confirmation=True,
    )


def reserve_generation_usage(
    db: Session,
    user_id: int,
    chatbot_type: str,
    now: datetime,
    free_limit: int,
    max_accepted_credits: int,
) -> Reservation:
    """무료 우선, 그 다음 사용자 승인 상한과 DB CAS로 실제 사용량을 예약합니다."""
    if max_accepted_credits < 0:
        raise ValueError("max_accepted_credits는 0 이상이어야 합니다.")

    cost = credit_cost_for(chatbot_type)
    free_reservation = try_reserve_free_usage(db, user_id, now, free_limit)
    if free_reservation is not None:
        return free_reservation

    if cost > max_accepted_credits:
        raise BillingConfirmationRequired(
            required=cost,
            accepted=max_accepted_credits,
        )

    result = db.execute(
        update(User)
        .where(User.id == user_id, User.credits >= cost)
        .values(credits=User.credits - cost)
        .execution_options(synchronize_session=False)
    )
    if result.rowcount != 1:
        current = db.scalar(select(User.credits).where(User.id == user_id))
        if current is None:
            raise ValueError("존재하지 않는 user_id입니다.")
        raise InsufficientCredits(required=cost, current=current)

    return CreditReservation(plan="paid", credits_used=cost)


def settle_generation_usage(reservation: Reservation) -> None:
    """성공 DB commit 뒤 Reservation을 settled terminal state로 확정합니다."""
    if isinstance(reservation, UsageReservation):
        settle_free_usage(reservation)
        return
    if isinstance(reservation, CreditReservation):
        if reservation.state == "pending" and not reservation.compensation_applied:
            reservation.state = "settled"
        return
    raise ValueError("지원하지 않는 Reservation 타입입니다.")


def apply_generation_usage_rollback(
    db: Session,
    user_id: int,
    reservation: Reservation,
    now: datetime,
) -> None:
    """commit된 예약의 실패 보상 DB mutation을 현재 transaction에 최대 1회 적용합니다."""
    if isinstance(reservation, UsageReservation):
        apply_free_usage_rollback(db, user_id, reservation, now)
        return
    if isinstance(reservation, CreditReservation):
        if reservation.state != "pending" or reservation.compensation_applied:
            return
        db.execute(
            update(User)
            .where(User.id == user_id)
            .values(credits=User.credits + reservation.credits_used)
            .execution_options(synchronize_session=False)
        )
        reservation.compensation_applied = True
        return
    raise ValueError("지원하지 않는 Reservation 타입입니다.")


def reset_generation_usage_rollback(reservation: Reservation) -> None:
    """보상 transaction rollback 뒤 transient marker를 재시도 가능 상태로 되돌립니다."""
    if isinstance(reservation, UsageReservation):
        reset_free_usage_rollback(reservation)
        return
    if isinstance(reservation, CreditReservation):
        if reservation.state == "pending":
            reservation.compensation_applied = False
        return
    raise ValueError("지원하지 않는 Reservation 타입입니다.")


def finalize_generation_usage_rollback(reservation: Reservation) -> None:
    """보상 DB commit 성공 뒤 Reservation을 rolled_back으로 확정합니다."""
    if isinstance(reservation, UsageReservation):
        finalize_free_usage_rollback(reservation)
        return
    if isinstance(reservation, CreditReservation):
        if reservation.state == "pending" and reservation.compensation_applied:
            reservation.state = "rolled_back"
            reservation.compensation_applied = False
        return
    raise ValueError("지원하지 않는 Reservation 타입입니다.")
