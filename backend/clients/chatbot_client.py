import asyncio
import importlib
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
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
        max_workers: int = 2,
        executor: ThreadPoolExecutor | None = None,
    ) -> None:
        self._basic = basic_callable
        self._consultant = consultant_callable
        self._timeout_seconds = timeout_seconds
        self._executor = executor or ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix="model-worker",
        )

    def close(self) -> None:
        """모델 전용 worker를 종료합니다(앱 shutdown 시 호출)."""
        self._executor.shutdown(wait=False, cancel_futures=True)

    async def generate(self, request: ModelRequest) -> ModelResult:
        payload = request.model_dump(mode="python", by_alias=True)
        if request.chatbot_type == "basic":
            model_callable = self._basic
        elif request.chatbot_type == "consultant":
            model_callable = self._consultant
        else:
            raise ValueError("chatbot_type은 basic 또는 consultant여야 합니다.")

        loop = asyncio.get_running_loop()
        raw_result = await asyncio.wait_for(
            loop.run_in_executor(self._executor, model_callable, payload),
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
        raise RuntimeError(  # noqa: TRY004 - 런타임 모듈 계약 위반을 공통 오류로 노출합니다.
            f"{module_name}.run callable을 찾을 수 없습니다."
        )
    return run


def preload_actual_model_weights() -> None:
    """실제 모델 런타임의 Hugging Face 가중치를 앱 기동 시 미리 로드합니다."""
    module = importlib.import_module("models.basic.nodes.image_review")
    preload = getattr(module, "preload_clip", None)
    if not callable(preload):
        raise RuntimeError(  # noqa: TRY004 - 런타임 모델 계약 위반을 공통 오류로 노출합니다.
            "models.basic.nodes.image_review.preload_clip callable을 찾을 수 없습니다."
        )
    preload()


def create_chatbot_client(settings: "Settings") -> ChatbotClient:
    """런타임 설정에 따라 Mock 또는 Actual 모델 Client를 조립합니다."""
    if settings.chatbot_mode == "mock":
        return MockChatbotClient()
    if settings.chatbot_mode == "actual":
        return ActualChatbotClient(
            _load_model_entrypoint("models.basic.main"),
            _load_model_entrypoint("models.consult.main"),
            timeout_seconds=settings.model_request_timeout_seconds,
            max_workers=settings.model_thread_pool_workers,
        )
    raise ValueError("chatbot_mode는 mock 또는 actual이어야 합니다.")
