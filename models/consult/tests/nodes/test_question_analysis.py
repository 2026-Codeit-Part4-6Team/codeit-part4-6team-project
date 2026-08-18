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


def _state(question: str, tokens_used: int = 0) -> dict:
    return {
        "chatbot_type": "consultant",
        "user_id": 1,
        "question": question,
        "store": _STORE,
        "tokens_used": tokens_used,
    }


def _response(payload, tokens: int = 100) -> tuple[str, int]:
    text = json.dumps(payload) if not isinstance(payload, str) else payload
    return text, tokens


@patch("models.consult.nodes.question_analysis.call_llm")
def test_rewrites_question_and_stores_analysis(mock_call_llm) -> None:
    mock_call_llm.return_value = _response(
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
    mock_call_llm.return_value = _response(
        {"rewritten_question": "질문", "is_sufficient": True, "missing_info": []}
    )

    question_analysis(_state("여기 어때요?"))

    system_prompt, user_prompt = mock_call_llm.call_args.args
    assert "여기 어때요?" in user_prompt
    assert "카페 코드잇" in user_prompt
    assert "카페" in user_prompt
    assert "JSON" in system_prompt


@patch("models.consult.nodes.question_analysis.call_llm")
def test_does_not_request_json_mode(mock_call_llm) -> None:
    """json_mode를 켜지 않는다 — 이 노드의 존재 이유가 "비JSON 응답도 폴백으로 버틴다"인데,
    json_mode로 비JSON 응답 자체를 원천 차단하면 그 폴백 경로가 실전에서 거의 실행되지
    않게 되어 폴백 테스트들이 지키는 시나리오가 유명무실해진다(PM 리뷰, PR #93)."""
    mock_call_llm.return_value = _response(
        {"rewritten_question": "질문", "is_sufficient": True, "missing_info": []}
    )

    question_analysis(_state("여기 어때요?"))

    assert mock_call_llm.call_args.kwargs.get("json_mode") is not True


@patch("models.consult.nodes.question_analysis.call_llm")
def test_passes_deadline_from_state_to_call_llm(mock_call_llm) -> None:
    """security_input이 세팅한 state["deadline"]을 그대로 call_llm에 넘겨, 이 노드
    호출이 그래프 전체 예산을 나눠 쓰게 한다(PM 리뷰, PR #93)."""
    mock_call_llm.return_value = _response(
        {"rewritten_question": "질문", "is_sufficient": True, "missing_info": []}
    )
    state = _state("여기 어때요?")
    state["deadline"] = 1234.5

    question_analysis(state)

    assert mock_call_llm.call_args.kwargs.get("deadline") == 1234.5


@patch("models.consult.nodes.question_analysis.call_llm")
def test_accumulates_tokens_used(mock_call_llm) -> None:
    mock_call_llm.return_value = _response(
        {"rewritten_question": "질문", "is_sufficient": True, "missing_info": []},
        tokens=150,
    )

    result = question_analysis(_state("여기 어때요?", tokens_used=50))

    assert result["tokens_used"] == 200


@patch("models.consult.nodes.question_analysis.call_llm")
def test_falls_back_when_response_is_not_json(mock_call_llm) -> None:
    mock_call_llm.return_value = _response("이건 JSON이 아님")

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
        # is_sufficient와 missing_info가 서로 모순되는 경우
        {"rewritten_question": "질문", "is_sufficient": True, "missing_info": ["주소"]},
        {"rewritten_question": "질문", "is_sufficient": False, "missing_info": []},
    ],
)
@patch("models.consult.nodes.question_analysis.call_llm")
def test_falls_back_on_wrong_shape(mock_call_llm, malformed_payload) -> None:
    mock_call_llm.return_value = _response(malformed_payload)

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


@patch("models.consult.nodes.question_analysis.call_llm")
def test_fallback_missing_info_not_shared_across_calls(mock_call_llm) -> None:
    """폴백에서 반환한 missing_info 리스트를 호출자가 수정해도 다음 호출의 폴백에 남지 않는다."""
    mock_call_llm.return_value = _response("이건 JSON이 아님")

    first = question_analysis(_state("첫 번째 질문"))
    first["context"]["question_analysis"]["missing_info"].append("오염된 값")

    second = question_analysis(_state("두 번째 질문"))

    assert second["context"]["question_analysis"]["missing_info"] == []
