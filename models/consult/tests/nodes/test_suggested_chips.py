# models/consult/nodes/suggested_chips.py 테스트 (D6 섹션 3)
import json
from unittest.mock import patch

import httpx
import openai
import pytest

from models.consult.nodes.suggested_chips import _FALLBACK_CHIPS, suggested_chips

_STORE = {
    "name": "카페 코드잇",
    "type": "카페",
    "address": "서울 강남구 역삼동",
    "lat": 37.5,
    "lng": 127.0,
}

_CHIPS = ["어떤 메뉴가 잘 팔릴까요?", "프로모션은 언제가 좋을까요?", "타겟 고객은 누구로 할까요?"]


def _state(
    question: str = "우리 카페 어떻게 홍보하면 좋을까요?",
    missing_info: list[str] | None = None,
    tokens_used: int = 0,
) -> dict:
    return {
        "chatbot_type": "consultant",
        "user_id": 1,
        "question": question,
        "store": _STORE,
        "context": {"question_analysis": {"is_sufficient": True, "missing_info": missing_info or [], "keyword": None}},
        "tokens_used": tokens_used,
    }


def _state_without_context(question: str = "우리 카페 어떻게 홍보하면 좋을까요?") -> dict:
    return {
        "chatbot_type": "consultant",
        "user_id": 1,
        "question": question,
        "store": _STORE,
    }


def _response(payload, tokens: int = 80) -> tuple[str, int]:
    text = json.dumps(payload, ensure_ascii=False) if not isinstance(payload, str) else payload
    return text, tokens


@patch("models.consult.nodes.suggested_chips.call_llm")
def test_returns_three_chips_from_llm(mock_call_llm) -> None:
    mock_call_llm.return_value = _response({"chips": _CHIPS})

    result = suggested_chips(_state())

    assert result["suggested_chips"] == _CHIPS


@patch("models.consult.nodes.suggested_chips.call_llm")
def test_requests_json_mode(mock_call_llm) -> None:
    mock_call_llm.return_value = _response({"chips": _CHIPS})

    suggested_chips(_state())

    assert mock_call_llm.call_args.kwargs.get("json_mode") is True


@patch("models.consult.nodes.suggested_chips.call_llm")
def test_passes_deadline_from_state_to_call_llm(mock_call_llm) -> None:
    """security_input이 세팅한 state["deadline"]을 그대로 call_llm에 넘긴다(PM 리뷰, PR #93)."""
    mock_call_llm.return_value = _response({"chips": _CHIPS})
    state = _state()
    state["deadline"] = 1234.5

    suggested_chips(state)

    assert mock_call_llm.call_args.kwargs.get("deadline") == 1234.5


@patch("models.consult.nodes.suggested_chips.call_llm")
def test_accumulates_tokens_used(mock_call_llm) -> None:
    mock_call_llm.return_value = _response({"chips": _CHIPS}, tokens=90)

    result = suggested_chips(_state(tokens_used=10))

    assert result["tokens_used"] == 100


@patch("models.consult.nodes.suggested_chips.call_llm")
def test_passes_question_and_store_info_to_prompt(mock_call_llm) -> None:
    mock_call_llm.return_value = _response({"chips": _CHIPS})

    suggested_chips(_state("우리 카페 어떻게 홍보하면 좋을까요?"))

    system_prompt, user_prompt = mock_call_llm.call_args.args
    assert "우리 카페 어떻게 홍보하면 좋을까요?" in user_prompt
    assert "카페 코드잇" in user_prompt
    assert "마케팅 컨설턴트" in system_prompt


@patch("models.consult.nodes.suggested_chips.call_llm")
def test_includes_missing_info_when_available(mock_call_llm) -> None:
    mock_call_llm.return_value = _response({"chips": _CHIPS})

    suggested_chips(_state(missing_info=["예산", "타겟 고객"]))

    _, user_prompt = mock_call_llm.call_args.args
    assert "예산" in user_prompt
    assert "타겟 고객" in user_prompt


@patch("models.consult.nodes.suggested_chips.call_llm")
def test_omits_missing_info_section_when_empty(mock_call_llm) -> None:
    mock_call_llm.return_value = _response({"chips": _CHIPS})

    suggested_chips(_state(missing_info=[]))

    _, user_prompt = mock_call_llm.call_args.args
    assert "부족한 정보" not in user_prompt


@patch("models.consult.nodes.suggested_chips.call_llm")
def test_strips_whitespace_from_chips(mock_call_llm) -> None:
    mock_call_llm.return_value = _response({"chips": ["  질문 하나\n", "질문 둘", "질문 셋"]})

    result = suggested_chips(_state())

    assert result["suggested_chips"] == ["질문 하나", "질문 둘", "질문 셋"]


@patch("models.consult.nodes.suggested_chips.call_llm")
def test_falls_back_when_response_is_not_json(mock_call_llm) -> None:
    mock_call_llm.return_value = _response("이건 JSON이 아님")

    result = suggested_chips(_state())

    assert result["suggested_chips"] == _FALLBACK_CHIPS


@pytest.mark.parametrize(
    "malformed_payload",
    [
        {"chips": []},  # 0개
        {"chips": ["질문 하나", "질문 둘"]},  # 2개(3개 미만)
        {"chips": ["질문 하나", "질문 둘", "질문 셋", "질문 넷"]},  # 4개(3개 초과)
        {"chips": ["질문 하나", "", "질문 셋"]},  # 빈 문자열
        {"chips": ["질문 하나", "   ", "질문 셋"]},  # 공백뿐
        {"chips": ["질문 하나", 123, "질문 셋"]},  # 문자열이 아닌 항목
        {"chips": "질문 하나, 질문 둘, 질문 셋"},  # chips가 리스트가 아님
        {"chips": None},  # chips가 null
        {},  # chips 필드 자체가 없음
        ["질문 하나", "질문 둘", "질문 셋"],  # 최상위가 dict가 아님
        "그냥 문자열",
    ],
)
@patch("models.consult.nodes.suggested_chips.call_llm")
def test_falls_back_on_wrong_shape(mock_call_llm, malformed_payload) -> None:
    mock_call_llm.return_value = _response(malformed_payload)

    result = suggested_chips(_state())

    assert result["suggested_chips"] == _FALLBACK_CHIPS


@patch("models.consult.nodes.suggested_chips.call_llm")
def test_fallback_chips_not_shared_across_calls(mock_call_llm) -> None:
    """폴백에서 반환한 리스트를 호출자가 수정해도 다음 호출의 폴백에 남지 않는다.

    _FALLBACK_CHIPS 자체를 비교 기준으로 쓰면, 구현이 그 리스트를 그대로(복사 없이)
    반환하는 회귀가 생겨도 first가 오염시킨 바로 그 객체를 second도 똑같이 참조하게
    돼 "같다"는 비교가 트루가 되어버려 회귀를 못 잡는다(실제로 재현됨) — 그래서
    독립된 리터럴 값과 비교하고, 두 반환 리스트가 서로 다른 객체인지(`is not`)도
    확인한다."""
    mock_call_llm.return_value = _response("이건 JSON이 아님")

    first = suggested_chips(_state("첫 번째 질문"))
    first["suggested_chips"].append("오염된 값")

    second = suggested_chips(_state("두 번째 질문"))

    assert second["suggested_chips"] is not first["suggested_chips"]
    assert second["suggested_chips"] == [
        "어떤 이벤트가 효과적일까요?",
        "가격을 어떻게 책정하면 좋을까요?",
        "주요 타겟 고객층은 어떻게 설정해야 할까요?",
    ]
    assert "오염된 값" not in second["suggested_chips"]


@patch("models.consult.nodes.suggested_chips.call_llm")
def test_omits_missing_info_section_when_context_missing_entirely(mock_call_llm) -> None:
    """question_analysis가 아직 안 돈 상태(그래프 조기 실행 등)에서도 죽지 않는다."""
    mock_call_llm.return_value = _response({"chips": _CHIPS})

    result = suggested_chips(_state_without_context())

    assert result["suggested_chips"] == _CHIPS


@patch("models.consult.nodes.suggested_chips.call_llm")
def test_propagates_call_llm_failure(mock_call_llm) -> None:
    """call_llm()이 재시도 끝에 예외를 던지면(완전 실패) 그대로 전파한다."""
    request = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")
    response = httpx.Response(status_code=429, request=request)
    mock_call_llm.side_effect = openai.RateLimitError("rate limited", response=response, body=None)

    with pytest.raises(openai.RateLimitError):
        suggested_chips(_state())
