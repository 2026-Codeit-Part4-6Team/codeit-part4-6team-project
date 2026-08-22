from typing import Protocol, runtime_checkable

from backend.schemas import ModelRequest, ModelResult


@runtime_checkable
class ChatbotClient(Protocol):
    """Service가 챗봇 구현을 호출하는 공통 경계."""

    async def generate(self, request: ModelRequest) -> ModelResult:
        """계약에 맞는 모델 결과를 반환합니다."""
        ...


class MockChatbotClient:
    """D4에서 Basic/Consultant Mock을 하나의 Client 경계로 라우팅합니다."""

    def __init__(self) -> None:
        from backend.clients.mock_chatbot import (
            MockBasicChatbotClient,
            MockConsultantChatbotClient,
        )

        self._basic = MockBasicChatbotClient()
        self._consultant = MockConsultantChatbotClient()

    async def generate(self, request: ModelRequest) -> ModelResult:
        if request.chatbot_type == "basic":
            return await self._basic.generate(request)
        if request.chatbot_type == "consultant":
            return await self._consultant.generate(request)
        raise ValueError("chatbot_type은 basic 또는 consultant여야 합니다.")
