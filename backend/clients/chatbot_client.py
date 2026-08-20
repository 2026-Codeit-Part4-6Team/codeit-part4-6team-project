import asyncio
import importlib
from collections.abc import Callable
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

from backend.schemas import MODEL_RESULT_ADAPTER, ModelRequest, ModelResult

if TYPE_CHECKING:
    from backend.config import Settings

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
        timeout_seconds: int,
    ) -> None:
        self._basic = basic_callable
        self._consultant = consultant_callable
        self._timeout_seconds = timeout_seconds

    async def generate(self, request: ModelRequest) -> ModelResult:
        payload = request.model_dump(mode="python", by_alias=True)
        if request.chatbot_type == "basic":
            model_callable = self._basic
        elif request.chatbot_type == "consultant":
            model_callable = self._consultant
        else:
            raise ValueError("chatbot_type은 basic 또는 consultant여야 합니다.")

        raw_result = await asyncio.wait_for(
            asyncio.to_thread(model_callable, payload),
            timeout=self._timeout_seconds,
        )
        return MODEL_RESULT_ADAPTER.validate_python(
            raw_result,
            chatbot_type=request.chatbot_type,
        )


def _load_model_entrypoint(module_name: str) -> SyncModelCallable:
    module = importlib.import_module(module_name)
    run = getattr(module, "run", None)
    if not callable(run):
        raise RuntimeError(f"{module_name}.run callable을 찾을 수 없습니다.")
    return run


def create_chatbot_client(settings: "Settings") -> ChatbotClient:
    """런타임 설정에 따라 Mock 또는 Actual 모델 Client를 조립합니다."""
    if settings.chatbot_mode == "mock":
        return MockChatbotClient()
    if settings.chatbot_mode == "actual":
        return ActualChatbotClient(
            _load_model_entrypoint("models.basic.main"),
            _load_model_entrypoint("models.consult.main"),
            timeout_seconds=settings.model_request_timeout_seconds,
        )
    raise ValueError("chatbot_mode는 mock 또는 actual이어야 합니다.")
