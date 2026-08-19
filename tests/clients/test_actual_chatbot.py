import asyncio

import pytest
from pydantic import ValidationError

from backend.clients import chatbot_client
from backend.schemas import (
    BasicModelResult,
    ConsultantModelResult,
    ConsultantSourceContext,
    ConsultantStrategy,
    ModelRequest,
    StoreContext,
)


def _store() -> StoreContext:
    return StoreContext(
        name="카페 코드잇",
        type="카페",
        address="서울 강남구",
        lat=37.5,
        lng=127.0,
    )


def _basic_request(*, with_source_context: bool = False) -> ModelRequest:
    source_context = None
    if with_source_context:
        source_context = ConsultantSourceContext(
            generation_id=7,
            strategy=ConsultantStrategy(
                summary="직장인 점심 수요가 높습니다.",
                actions=[{"type": "target", "content": "직장인을 집중 공략합니다."}],
            ),
            reasons=["오피스 밀집 지역"],
            sources=["상권분석"],
        )
    return ModelRequest(
        chatbot_type="basic",
        user_id=1,
        question="신메뉴 광고를 만들어줘",
        platform="instagram",
        store=_store(),
        source_context=source_context,
    )


def _consultant_request() -> ModelRequest:
    return ModelRequest(
        chatbot_type="consultant",
        user_id=1,
        question="우리 가게 전략을 알려줘",
        platform=None,
        store=_store(),
    )


def _basic_result() -> dict:
    return {
        "status": "ok",
        "title": "신메뉴 광고",
        "proposals": [
            {"copy": "제안 1", "image_b64": None, "error": None},
            {"copy": "제안 2", "image_b64": None, "error": None},
            {"copy": "제안 3", "image_b64": None, "error": None},
        ],
        "sources": ["상권분석"],
        "tokens_used": 10,
        "suggested_chips": [],
    }


def _consultant_result() -> dict:
    return {
        "status": "ok",
        "title": "카페 전략",
        "strategy": {
            "summary": "직장인 수요를 공략합니다.",
            "actions": [
                {"type": "target", "content": "직장인 타깃 프로모션을 운영합니다."}
            ],
        },
        "reasons": ["오피스 밀집 지역"],
        "sources": ["상권분석"],
        "tokens_used": 12,
        "suggested_chips": ["메뉴 전략은?", "가격 전략은?", "홍보 채널은?"],
    }


def test_actual_client_dispatches_basic_and_preserves_source_context():
    calls = []

    def basic_run(payload):
        calls.append(("basic", payload))
        return _basic_result()

    def consultant_run(_payload):
        raise AssertionError("consultant callable must not be called")

    client = chatbot_client.ActualChatbotClient(basic_run, consultant_run, timeout_seconds=60)

    result = asyncio.run(client.generate(_basic_request(with_source_context=True)))

    assert isinstance(result, BasicModelResult)
    assert calls[0][0] == "basic"
    payload = calls[0][1]
    assert isinstance(payload, dict)
    assert payload["source_context"]["generation_id"] == 7
    assert payload["source_context"]["strategy"]["actions"][0]["type"] == "target"


def test_actual_client_dispatches_consultant():
    def basic_run(_payload):
        raise AssertionError("basic callable must not be called")

    seen = []

    def consultant_run(payload):
        seen.append(payload)
        return _consultant_result()

    client = chatbot_client.ActualChatbotClient(basic_run, consultant_run, timeout_seconds=60)

    result = asyncio.run(client.generate(_consultant_request()))

    assert isinstance(result, ConsultantModelResult)
    assert seen[0]["chatbot_type"] == "consultant"
    assert seen[0]["platform"] is None


def test_actual_client_executes_sync_callable_via_to_thread(monkeypatch):
    captured = []

    async def fake_to_thread(func, *args):
        captured.append((func, args))
        return func(*args)

    monkeypatch.setattr(chatbot_client.asyncio, "to_thread", fake_to_thread)

    def basic_run(_payload):
        return _basic_result()

    client = chatbot_client.ActualChatbotClient(
        basic_run,
        lambda _payload: _consultant_result(),
        timeout_seconds=60,
    )

    asyncio.run(client.generate(_basic_request()))

    assert captured
    assert captured[0][0] is basic_run
    assert isinstance(captured[0][1][0], dict)


def test_actual_client_validates_raw_output():
    client = chatbot_client.ActualChatbotClient(
        lambda _payload: {"status": "ok", "title": "broken"},
        lambda _payload: _consultant_result(),
        timeout_seconds=60,
    )

    with pytest.raises(ValidationError):
        asyncio.run(client.generate(_basic_request()))


def test_actual_client_propagates_model_exception():
    def basic_run(_payload):
        raise RuntimeError("provider exploded")

    client = chatbot_client.ActualChatbotClient(
        basic_run,
        lambda _payload: _consultant_result(),
        timeout_seconds=60,
    )

    with pytest.raises(RuntimeError, match="provider exploded"):
        asyncio.run(client.generate(_basic_request()))


def test_actual_client_applies_configured_timeout_to_sync_run(monkeypatch):
    captured = []
    real_wait_for = asyncio.wait_for

    async def fake_wait_for(awaitable, *, timeout):
        captured.append(timeout)
        return await real_wait_for(awaitable, timeout=1)

    monkeypatch.setattr(chatbot_client.asyncio, "wait_for", fake_wait_for)

    client = chatbot_client.ActualChatbotClient(
        lambda _payload: _basic_result(),
        lambda _payload: _consultant_result(),
        timeout_seconds=73,
    )

    asyncio.run(client.generate(_basic_request()))

    assert captured == [73]
