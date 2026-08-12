# models/consult/nodes/question_analysis.py 테스트
import json
from unittest.mock import patch

import httpx
import openai
import pytest

from models.consult.nodes.question_analysis import question_analysis

_STORE = {
    "name": "카페 코드잇",
    "type": "카페",
    "address": "서울 강남구 역삼동",
    "lat": 37.5,
    "lng": 127.0,
}


def _state(question: str) -> dict:
    return {
        "chatbot_type": "consultant",
        "user_id": 1,
        "question": question,
        "store": _STORE,
    }


@patch("models.consult.nodes.question_analysis.call_llm")
def test_rewrites_question_and_stores_analysis(mock_call_llm) -> None:
    mock_call_llm.return_value = json.dumps(
        {
            "rewritten_question": "카페 코드잇 장사가 잘 될까요?",
            "is_sufficient": True,
            "missing_info": [],
        }
    )

    result = question_analysis(_state("여기 장사 잘될까요?"))

    assert result["question"] == "카페 코드잇 장사가 잘 될까요?"
    assert result["context"]["question_analysis"] == {
        "is_sufficient": True,
        "missing_info": [],
    }


@patch("models.consult.nodes.question_analysis.call_llm")
def test_passes_question_and_store_info_to_llm(mock_call_llm) -> None:
    mock_call_llm.return_value = json.dumps(
        {"rewritten_question": "질문", "is_sufficient": True, "missing_info": []}
    )

    question_analysis(_state("여기 어때요?"))

    system_prompt, user_prompt = mock_call_llm.call_args.args
    assert "여기 어때요?" in user_prompt
    assert "카페 코드잇" in user_prompt
    assert "카페" in user_prompt
    assert "JSON" in system_prompt


@patch("models.consult.nodes.question_analysis.call_llm")
def test_falls_back_when_response_is_not_json(mock_call_llm) -> None:
    mock_call_llm.return_value = "이건 JSON이 아님"

    result = question_analysis(_state("원본 질문"))

    assert result["question"] == "원본 질문"
    assert result["context"]["question_analysis"] == {
        "is_sufficient": True,
        "missing_info": [],
    }


@pytest.mark.parametrize(
    "malformed_payload",
    [
        {"rewritten_question": "", "is_sufficient": True, "missing_info": []},
        {"rewritten_question": None, "is_sufficient": True, "missing_info": []},
        {"rewritten_question": "질문", "is_sufficient": "yes", "missing_info": []},
        {"rewritten_question": "질문", "is_sufficient": True, "missing_info": "없음"},
        {"rewritten_question": "질문", "is_sufficient": True, "missing_info": [1, 2]},
        {"rewritten_question": "질문", "is_sufficient": True},
        {"is_sufficient": True, "missing_info": []},
        ["질문", True, []],
        "그냥 문자열",
    ],
)
@patch("models.consult.nodes.question_analysis.call_llm")
def test_falls_back_on_wrong_shape(mock_call_llm, malformed_payload) -> None:
    mock_call_llm.return_value = json.dumps(malformed_payload)

    result = question_analysis(_state("원본 질문"))

    assert result["question"] == "원본 질문"
    assert result["context"]["question_analysis"] == {
        "is_sufficient": True,
        "missing_info": [],
    }


@patch("models.consult.nodes.question_analysis.call_llm")
def test_propagates_call_llm_failure(mock_call_llm) -> None:
    """call_llm()이 재시도 끝에 예외를 던지면(완전 실패) 그대로 전파한다 — 폴백하지 않는다."""
    request = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")
    response = httpx.Response(status_code=429, request=request)
    mock_call_llm.side_effect = openai.RateLimitError("rate limited", response=response, body=None)

    with pytest.raises(openai.RateLimitError):
        question_analysis(_state("원본 질문"))
