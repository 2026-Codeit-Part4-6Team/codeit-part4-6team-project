import asyncio

import pytest

from backend.clients.chatbot_client import ChatbotClient
from backend.clients.mock_chatbot import (
    MockBasicChatbotClient,
    MockConsultantChatbotClient,
)
from backend.schemas import ModelRequest, StoreContext


def make_request(chatbot_type: str) -> ModelRequest:
    """챗봇 종류에 맞는 모델 요청을 생성합니다."""
    return ModelRequest(
        chatbot_type=chatbot_type,
        user_id=1,
        question="광고 전략을 알려줘",
        platform="instagram" if chatbot_type == "basic" else None,
        store=StoreContext(
            name="카페 코드잇",
            type="카페",
            address="서울 강남구",
            lat=37.5,
            lng=127.0,
        ),
    )


async def call_client(client: ChatbotClient, request: ModelRequest):
    """공통 Client Protocol로 모델을 호출합니다."""
    return await client.generate(request)


def test_basic_mock_returns_three_contract_slots():
    """Basic Mock은 계약된 세 Proposal을 반환합니다."""
    result = asyncio.run(call_client(MockBasicChatbotClient(), make_request("basic")))

    assert len(result.proposals) == 3
    assert result.suggested_chips == []
    assert all(proposal.copy for proposal in result.proposals)


def test_consultant_mock_returns_strategy_and_three_chips():
    """Consultant Mock은 전략과 추천 질문 세 개를 반환합니다."""
    result = asyncio.run(
        call_client(MockConsultantChatbotClient(), make_request("consultant"))
    )

    assert result.strategy.summary
    assert result.reasons
    assert len(result.suggested_chips) == 3


@pytest.mark.parametrize(
    ("client", "request_type"),
    [
        (MockBasicChatbotClient(), "consultant"),
        (MockConsultantChatbotClient(), "basic"),
    ],
)
def test_mock_rejects_wrong_chatbot_type(client, request_type):
    """Mock은 자신과 다른 챗봇 요청을 거부합니다."""
    with pytest.raises(ValueError, match="chatbot_type"):
        asyncio.run(call_client(client, make_request(request_type)))
