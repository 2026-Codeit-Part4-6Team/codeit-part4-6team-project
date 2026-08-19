"""
models/shared/tests/test_llm.py 
— 공통 OpenAI 호출 래퍼 테스트

models/shared/llm.py 검증.

컨설턴트 구현본(D-035) 테스트 5종을 이관하고, 통합 시 추가된
(text, tokens) 반환 · json_mode · 요청 데드라인(D-052) 3종을 더했다.
"""
import time
from unittest.mock import MagicMock, call, patch

import httpx
import openai
import pytest

from models.shared.config import (
    LLM_MAX_RETRIES,
    LLM_TIMEOUT_SECONDS,
    OPENAI_BASE_URL,
    OPENAI_MODEL,
)
from models.shared.llm import call_llm, get_total_tokens, reset_client, reset_total_tokens


# ── 공통 헬퍼 ────────────────────────────────────────────────
def _rate_limit_error() -> openai.RateLimitError:
    """실제 429 응답을 흉내 낸 RateLimitError 인스턴스를 만든다."""
    request = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")
    response = httpx.Response(status_code=429, request=request)
    return openai.RateLimitError("rate limited", response=response, body=None)


def _fake_response(content: str | None, tokens: int = 12) -> MagicMock:
    """OpenAI 응답 객체를 흉내 낸다(usage 포함 — 토큰 반환 검증에 필요)."""
    response = MagicMock()
    response.choices = [MagicMock(message=MagicMock(content=content))]
    response.usage = MagicMock(total_tokens=tokens)
    return response

    
@pytest.fixture(autouse=True)
def _reset_singleton():
    """싱글턴 클라이언트와 토큰 카운터가 테스트 간에 새어나가지 않게 한다(D-088)."""
    reset_client()
    reset_total_tokens()
    yield
    reset_client()
    reset_total_tokens()


# ── 이관분: 컨설턴트 구현본 테스트 5종 (D-035) ──────────────
@patch("models.shared.llm.time.sleep")
@patch("models.shared.llm.OpenAI")
def test_returns_content_on_success(mock_openai_cls, mock_sleep) -> None:
    """정상 응답이면 재시도 없이 텍스트를 반환한다."""
    client = MagicMock()
    client.chat.completions.create.return_value = _fake_response("안녕하세요")
    mock_openai_cls.return_value = client

    text, _ = call_llm("시스템 프롬프트", "사용자 프롬프트")

    assert text == "안녕하세요"
    mock_sleep.assert_not_called()
    mock_openai_cls.assert_called_once_with(
        max_retries=0, timeout=LLM_TIMEOUT_SECONDS, base_url=OPENAI_BASE_URL
    )
    called_kwargs = client.chat.completions.create.call_args.kwargs
    assert called_kwargs["messages"] == [
        {"role": "system", "content": "시스템 프롬프트"},
        {"role": "user", "content": "사용자 프롬프트"},
    ]


@patch("models.shared.llm.time.sleep")
@patch("models.shared.llm.OpenAI")
def test_retries_after_rate_limit_then_succeeds(mock_openai_cls, mock_sleep) -> None:
    """429 한 번 후 성공하면 2초 대기 뒤 정상 반환한다."""
    client = MagicMock()
    client.chat.completions.create.side_effect = [
        _rate_limit_error(),
        _fake_response("성공"),
    ]
    mock_openai_cls.return_value = client

    text, _ = call_llm("system", "user")

    assert text == "성공"
    mock_sleep.assert_called_once_with(2)


@patch("models.shared.llm.time.sleep")
@patch("models.shared.llm.OpenAI")
def test_raises_after_max_retries(mock_openai_cls, mock_sleep) -> None:
    """최초 호출 포함 총 4회 시도 후에도 429면 예외를 그대로 올린다."""
    client = MagicMock()
    client.chat.completions.create.side_effect = [
        _rate_limit_error() for _ in range(LLM_MAX_RETRIES + 1)
    ]
    mock_openai_cls.return_value = client

    with pytest.raises(openai.RateLimitError):
        call_llm("system", "user")

    assert client.chat.completions.create.call_count == LLM_MAX_RETRIES + 1
    assert mock_sleep.call_args_list == [call(2), call(4), call(8)]


@patch("models.shared.llm.time.sleep")
@patch("models.shared.llm.OpenAI")
def test_propagates_non_rate_limit_error_immediately(mock_openai_cls, mock_sleep) -> None:
    """429가 아닌 예외는 재시도 없이 즉시 전파한다."""
    client = MagicMock()
    client.chat.completions.create.side_effect = ValueError("boom")
    mock_openai_cls.return_value = client

    with pytest.raises(ValueError):
        call_llm("system", "user")

    assert client.chat.completions.create.call_count == 1
    mock_sleep.assert_not_called()


@patch("models.shared.llm.time.sleep")
@patch("models.shared.llm.OpenAI")
def test_raises_value_error_when_content_is_none(mock_openai_cls, mock_sleep) -> None:
    """content가 None이면 -> tuple[str, int] 계약을 지키기 위해 명시적으로 에러를 낸다."""
    client = MagicMock()
    client.chat.completions.create.return_value = _fake_response(None)
    mock_openai_cls.return_value = client

    with pytest.raises(ValueError):
        call_llm("system", "user")

    mock_sleep.assert_not_called()


# ── 추가분: 통합으로 생긴 기능 3종 ──────────────────────────
@patch("models.shared.llm.OpenAI")
def test_returns_text_and_tokens(mock_openai_cls) -> None:
    """계약 필수 필드인 tokens_used를 채울 수 있도록 토큰을 함께 반환한다(D-086)."""
    client = MagicMock()
    client.chat.completions.create.return_value = _fake_response("안녕하세요", 37)
    mock_openai_cls.return_value = client

    before = get_total_tokens()
    text, tokens = call_llm("system", "user")

    assert (text, tokens) == ("안녕하세요", 37)
    assert get_total_tokens() - before == 37  # 예산 모니터링 누적(D-092)


@patch("models.shared.llm.OpenAI")
def test_json_mode_sets_response_format(mock_openai_cls) -> None:
    """json_mode=True면 JSON 객체 응답을 강제한다."""
    client = MagicMock()
    client.chat.completions.create.return_value = _fake_response("{}")
    mock_openai_cls.return_value = client

    call_llm("system", "user", json_mode=True)

    kwargs = client.chat.completions.create.call_args.kwargs
    assert kwargs["response_format"] == {"type": "json_object"}


@patch("models.shared.llm.time.sleep")
@patch("models.shared.llm.OpenAI")
def test_gives_up_when_deadline_is_shorter_than_backoff(mock_openai_cls, mock_sleep) -> None:
    """남은 예산이 다음 대기시간보다 짧으면 자지 않고 즉시 전파한다(D-052)."""
    client = MagicMock()
    client.chat.completions.create.side_effect = _rate_limit_error()
    mock_openai_cls.return_value = client

    with pytest.raises(openai.RateLimitError):
        call_llm("system", "user", deadline=time.monotonic() + 1)

    assert client.chat.completions.create.call_count == 1
    mock_sleep.assert_not_called()
    

@patch("models.shared.llm.OpenAI")
def test_default_model_is_resolved_before_counting(mock_openai_cls) -> None:
    """model 을 생략하면 OPENAI_MODEL 로 호출하고 토큰도 그 이름으로 집계한다.

    raw model(None)을 집계 키로 쓰면 KeyError 가 나거나 모든 토큰이
    None 키에 쌓여 모델별 집계(D-257)가 무의미해진다.
    """
    client = MagicMock()
    client.chat.completions.create.return_value = _fake_response("응답", 21)
    mock_openai_cls.return_value = client

    call_llm("system", "user")

    assert client.chat.completions.create.call_args.kwargs["model"] == OPENAI_MODEL
    assert get_total_tokens(OPENAI_MODEL) == 21
    assert get_total_tokens() == 21          # 전체 합계도 같다


@patch("models.shared.llm.OpenAI")
def test_tokens_are_counted_per_model(mock_openai_cls) -> None:
    """생성 모델과 Judge 모델의 소비량이 분리 집계된다(D-257·D-251)."""
    client = MagicMock()
    client.chat.completions.create.side_effect = [
        _fake_response("생성 결과", 10),
        _fake_response("채점 결과", 30),
    ]
    mock_openai_cls.return_value = client

    call_llm("system", "user")                           # 생성 — OPENAI_MODEL
    call_llm("system", "user", model="judge-model-x")    # 채점 — Judge

    assert get_total_tokens(OPENAI_MODEL) == 10
    assert get_total_tokens("judge-model-x") == 30
    assert get_total_tokens() == 40


def test_unknown_model_returns_zero_instead_of_raising() -> None:
    """집계에 없는 모델을 조회해도 KeyError 가 아니라 0 이다."""
    assert get_total_tokens("존재하지-않는-모델") == 0