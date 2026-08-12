from dataclasses import dataclass
from typing import Literal

from backend.config import settings
from backend.models import User
from backend.schemas import ChatbotType


@dataclass(frozen=True)
class CreditReservation:
    """유료 생성 요청이 예약한 크레딧입니다."""

    credits_used: int
    plan: Literal["paid"] = "paid"
    free_count_incremented: Literal[False] = False


class InsufficientCredits(Exception):
    """사용자의 크레딧이 요청 비용보다 부족할 때 발생합니다."""

    def __init__(self, required: int, available: int) -> None:
        self.required = required
        self.available = available
        super().__init__(f"크레딧이 부족합니다: 필요 {required}, 보유 {available}")


def credit_cost_for(chatbot_type: ChatbotType) -> int:
    """챗봇 종류에 설정된 1회 생성 비용을 반환합니다."""
    if chatbot_type == "basic":
        return settings.basic_credit_cost
    return settings.consultant_credit_cost


def reserve_credits(user: User, chatbot_type: ChatbotType) -> CreditReservation:
    """잔액이 충분하면 챗봇별 비용을 차감하고 예약 정보를 반환합니다."""
    cost = credit_cost_for(chatbot_type)
    if user.credits < cost:
        raise InsufficientCredits(required=cost, available=user.credits)

    user.credits -= cost
    return CreditReservation(credits_used=cost)


def rollback_credits(user: User, reservation: CreditReservation) -> None:
    """예약에서 차감한 크레딧을 사용자 잔액에 복구합니다."""
    user.credits += reservation.credits_used
