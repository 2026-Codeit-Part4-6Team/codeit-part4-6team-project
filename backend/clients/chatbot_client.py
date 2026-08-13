from typing import Protocol, runtime_checkable

from backend.schemas import ModelRequest, ModelResult


@runtime_checkable
class ChatbotClient(Protocol):
    """Service가 챗봇 구현을 호출하는 공통 경계."""

    async def generate(self, request: ModelRequest) -> ModelResult:
        """계약에 맞는 모델 결과를 반환합니다."""
        ...
