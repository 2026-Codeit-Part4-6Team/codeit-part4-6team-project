# models/consult/nodes/strategy.py 테스트 (D4 섹션 1: 질문만으로 전략 생성)
from unittest.mock import patch

import httpx
import openai
import pytest

from models.consult.nodes.strategy import strategy

_STORE = {
    "name": "카페 코드잇",
    "type": "카페",
    "address": "서울 강남구 역삼동",
    "lat": 37.5,
    "lng": 127.0,
}


def _state(question: str = "우리 카페 어떻게 홍보하면 좋을까요?") -> dict:
    return {
        "chatbot_type": "consultant",
        "user_id": 1,
        "question": question,
        "store": _STORE,
    }


@patch("models.consult.nodes.strategy.call_llm")
def test_returns_summary_from_llm(mock_call_llm) -> None:
    mock_call_llm.return_value = "시즌 한정 메뉴로 신규 고객을 유입하세요."

    result = strategy(_state())

    assert result == {"result": {"summary": "시즌 한정 메뉴로 신규 고객을 유입하세요."}}


@patch("models.consult.nodes.strategy.call_llm")
def test_strips_leading_and_trailing_whitespace_from_summary(mock_call_llm) -> None:
    mock_call_llm.return_value = "  전략 내용\n"

    result = strategy(_state())

    assert result == {"result": {"summary": "전략 내용"}}


@patch("models.consult.nodes.strategy.call_llm")
def test_passes_question_and_store_info_to_prompt(mock_call_llm) -> None:
    mock_call_llm.return_value = "전략"

    strategy(_state("우리 카페 어떻게 홍보하면 좋을까요?"))

    system_prompt, user_prompt = mock_call_llm.call_args.args
    assert "우리 카페 어떻게 홍보하면 좋을까요?" in user_prompt
    assert "카페 코드잇" in user_prompt
    assert "카페" in user_prompt
    assert "마케팅 컨설턴트" in system_prompt


@patch("models.consult.nodes.strategy.call_llm")
def test_propagates_call_llm_failure(mock_call_llm) -> None:
    """call_llm()이 재시도 끝에 예외를 던지면(완전 실패) 그대로 전파한다 — 질문 분석 노드와 동일 원칙."""
    request = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")
    response = httpx.Response(status_code=429, request=request)
    mock_call_llm.side_effect = openai.RateLimitError("rate limited", response=response, body=None)

    with pytest.raises(openai.RateLimitError):
        strategy(_state())


@pytest.mark.parametrize("blank_summary", ["", "   ", "\n\t"])
@patch("models.consult.nodes.strategy.call_llm")
def test_raises_when_summary_is_blank(mock_call_llm, blank_summary) -> None:
    """빈 문자열·공백뿐인 요약은 계약(title/summary 빈 문자열 불가)을 어기므로 명시적으로 실패시킨다."""
    mock_call_llm.return_value = blank_summary

    with pytest.raises(ValueError):
        strategy(_state())
