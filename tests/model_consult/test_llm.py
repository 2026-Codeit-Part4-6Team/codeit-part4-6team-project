# model_consult/llm.py 테스트 — OpenAI 호출 재시도·백오프 검증
from unittest.mock import MagicMock, call, patch

import httpx
import openai
import pytest

from model_consult.llm import call_llm


def _rate_limit_error() -> openai.RateLimitError:
    request = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")
    response = httpx.Response(status_code=429, request=request)
    return openai.RateLimitError("rate limited", response=response, body=None)


def _fake_response(content: str) -> MagicMock:
    response = MagicMock()
    response.choices = [MagicMock(message=MagicMock(content=content))]
    return response


@patch("model_consult.llm.time.sleep")
@patch("model_consult.llm.OpenAI")
def test_call_llm_returns_content_on_success(mock_openai_cls, mock_sleep) -> None:
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = _fake_response("안녕하세요")
    mock_openai_cls.return_value = mock_client

    result = call_llm("시스템 프롬프트", "사용자 프롬프트")

    assert result == "안녕하세요"
    mock_sleep.assert_not_called()
    mock_openai_cls.assert_called_once_with(max_retries=0)

    called_kwargs = mock_client.chat.completions.create.call_args.kwargs
    assert called_kwargs["messages"] == [
        {"role": "system", "content": "시스템 프롬프트"},
        {"role": "user", "content": "사용자 프롬프트"},
    ]


@patch("model_consult.llm.time.sleep")
@patch("model_consult.llm.OpenAI")
def test_call_llm_retries_after_rate_limit_then_succeeds(mock_openai_cls, mock_sleep) -> None:
    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = [
        _rate_limit_error(),
        _fake_response("성공"),
    ]
    mock_openai_cls.return_value = mock_client

    result = call_llm("system", "user")

    assert result == "성공"
    mock_sleep.assert_called_once_with(2)


@patch("model_consult.llm.time.sleep")
@patch("model_consult.llm.OpenAI")
def test_call_llm_raises_after_max_retries(mock_openai_cls, mock_sleep) -> None:
    """최초 호출 포함 총 4회 시도(재시도 3회) 후에도 429면 예외를 그대로 올린다."""
    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = [_rate_limit_error() for _ in range(4)]
    mock_openai_cls.return_value = mock_client

    with pytest.raises(openai.RateLimitError):
        call_llm("system", "user")

    assert mock_client.chat.completions.create.call_count == 4
    assert mock_sleep.call_args_list == [call(2), call(4), call(8)]


@patch("model_consult.llm.time.sleep")
@patch("model_consult.llm.OpenAI")
def test_call_llm_propagates_non_rate_limit_error_immediately(
    mock_openai_cls, mock_sleep
) -> None:
    """RateLimitError가 아닌 예외는 재시도 없이 즉시 전파한다."""
    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = ValueError("boom")
    mock_openai_cls.return_value = mock_client

    with pytest.raises(ValueError):
        call_llm("system", "user")

    assert mock_client.chat.completions.create.call_count == 1
    mock_sleep.assert_not_called()


@patch("model_consult.llm.time.sleep")
@patch("model_consult.llm.OpenAI")
def test_call_llm_raises_value_error_when_content_is_none(mock_openai_cls, mock_sleep) -> None:
    """OpenAI 응답의 content가 None이면(SDK 타입상 Optional) -> str 계약을 지키기 위해 명시적으로 에러를 낸다."""
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = _fake_response(None)
    mock_openai_cls.return_value = mock_client

    with pytest.raises(ValueError):
        call_llm("system", "user")

    mock_sleep.assert_not_called()
