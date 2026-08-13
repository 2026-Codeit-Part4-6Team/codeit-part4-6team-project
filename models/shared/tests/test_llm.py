# models/shared/tests/test_llm.py (추가분만)
import time
from unittest.mock import MagicMock, patch

import openai
import pytest

from models.shared.llm import call_llm, get_total_tokens, reset_client


@pytest.fixture(autouse=True)
def _reset():
    """싱글턴 클라이언트가 테스트 간에 새어나가지 않게 한다."""
    reset_client()
    yield
    reset_client()


def _fake_response(content: str, tokens: int = 12) -> MagicMock:
    response = MagicMock()
    response.choices = [MagicMock(message=MagicMock(content=content))]
    response.usage = MagicMock(total_tokens=tokens)
    return response


@patch("models.shared.llm.OpenAI")
def test_returns_text_and_tokens(mock_openai_cls) -> None:
    """계약 필수 필드인 tokens_used를 채울 수 있도록 토큰을 함께 반환한다."""
    client = MagicMock()
    client.chat.completions.create.return_value = _fake_response("안녕하세요", 37)
    mock_openai_cls.return_value = client

    before = get_total_tokens()
    text, tokens = call_llm("system", "user")

    assert (text, tokens) == ("안녕하세요", 37)
    assert get_total_tokens() - before == 37     # 예산 모니터링 누적


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
    """남은 예산이 다음 대기시간보다 짧으면 자지 않고 즉시 전파한다 (D-049)."""
    client = MagicMock()
    client.chat.completions.create.side_effect = _rate_limit_error()
    mock_openai_cls.return_value = client

    with pytest.raises(openai.RateLimitError):
        call_llm("system", "user", deadline=time.monotonic() + 1)

    assert client.chat.completions.create.call_count == 1
    mock_sleep.assert_not_called()