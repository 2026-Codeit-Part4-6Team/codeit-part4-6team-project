import asyncio
from collections.abc import Callable
from typing import Any, Protocol, runtime_checkable

from backend.schemas import MODEL_RESULT_ADAPTER, ModelRequest, ModelResult

SyncModelCallable = Callable[[dict[str, Any]], object]


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


class ActualChatbotClient:
    """실제 Basic/Consultant 동기 entrypoint를 Service 경계에 연결합니다."""

    def __init__(
        self,
        basic_callable: SyncModelCallable,
        consultant_callable: SyncModelCallable,
    ) -> None:
        self._basic = basic_callable
        self._consultant = consultant_callable

    async def generate(self, request: ModelRequest) -> ModelResult:
        payload = request.model_dump(mode="python", by_alias=True)
        if request.chatbot_type == "basic":
            raw_result = await asyncio.to_thread(self._basic, payload)
        elif request.chatbot_type == "consultant":
            raw_result = await asyncio.to_thread(self._consultant, payload)
        else:
            raise ValueError("chatbot_type은 basic 또는 consultant여야 합니다.")

        return MODEL_RESULT_ADAPTER.validate_python(
            raw_result,
            chatbot_type=request.chatbot_type,
        )
