import json
from unittest.mock import patch

import httpx
import openai

from models.basic.nodes.question_analysis import question_analysis_node

_STORE = {
    "name": "카페 코드잇",
    "type": "카페",
    "address": "서울 강남구 역삼동",
    "lat": 37.5,
    "lng": 127.0,
}


def _rate_limit_error() -> openai.RateLimitError:
    request = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")
    response = httpx.Response(status_code=429, request=request)
    return openai.RateLimitError("rate limited", response=response, body=None)


def _state(**overrides):
    base = {
        "question": "여름 신메뉴 홍보 문구 만들어줘",
        "store": _STORE,
        "extra": {},
        "issues": [],
    }
    return {**base, **overrides}


@patch("models.basic.nodes.question_analysis.call_llm")
def test_sufficient_info_proceeds_with_rewritten_question(mock_call_llm):
    mock_call_llm.return_value = (
        json.dumps(
            {
                "sufficient": True,
                "rewritten_question": "여름 신메뉴 홍보 문구",
                "keyword": "여름 신메뉴",
                "message": "",
            }
        ),
        10,
    )

    result = question_analysis_node(_state())

    assert result["status"] == "ok"
    assert result["question"] == "여름 신메뉴 홍보 문구"
    assert result["keyword"] == "여름 신메뉴"


@patch("models.basic.nodes.question_analysis.call_llm")
def test_insufficient_info_without_extra_reasks(mock_call_llm):
    mock_call_llm.return_value = (
        json.dumps(
            {
                "sufficient": False,
                "rewritten_question": "광고 만들어줘",
                "message": "무엇을 광고하고 싶으신가요?",
            }
        ),
        10,
    )

    result = question_analysis_node(_state(question="광고 만들어줘"))

    assert result["status"] == "blocked"
    assert result["issues"][0]["action"] == "reask"
    assert result["issues"][0]["message"] == "무엇을 광고하고 싶으신가요?"


@patch("models.basic.nodes.question_analysis.call_llm")
def test_clarification_extra_makes_info_sufficient(mock_call_llm):
    mock_call_llm.return_value = (
        json.dumps(
            {
                "sufficient": True,
                "rewritten_question": "아이스 아메리카노 신메뉴 홍보",
                "keyword": "아이스 아메리카노",
                "message": "",
            }
        ),
        10,
    )

    result = question_analysis_node(
        _state(
            question="광고 만들어줘",
            extra={"clarification": "아이스 아메리카노 신메뉴예요"},
        )
    )

    assert result["status"] == "ok"
    assert result["question"] == "아이스 아메리카노 신메뉴 홍보"
    assert result["keyword"] == "아이스 아메리카노"


@patch("models.basic.nodes.question_analysis.call_llm")
def test_call_llm_exception_sets_error_status_with_classified_reason(mock_call_llm):
    mock_call_llm.side_effect = _rate_limit_error()

    result = question_analysis_node(_state())

    assert result["status"] == "error"
    assert result["issues"][0]["source"] == "question_analysis"
    assert result["issues"][0]["reason"] == "rate_limit"


@patch("models.basic.nodes.question_analysis.call_llm")
def test_missing_keyword_falls_back_to_rewritten_question(mock_call_llm):
    mock_call_llm.return_value = (
        json.dumps(
            {
                "sufficient": True,
                "rewritten_question": "여름 신메뉴 홍보 문구",
                "message": "",
            }
        ),
        10,
    )

    result = question_analysis_node(_state())

    assert result["keyword"] == "여름 신메뉴 홍보 문구"