# models/consult/nodes/strategy.py 테스트 (D4 섹션 1~3: 전략 생성 + 상권 데이터 주입)
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


_MARKET = {
    "total_count": 43,
    "same_industry_count": 12,
    "nearest_distance_m": 55,
    "density_tier": "높음",
    "industry_breakdown": {"카페": 12, "편의점": 5},
}


def _state(question: str = "우리 카페 어떻게 홍보하면 좋을까요?", market: dict | None = None) -> dict:
    return {
        "chatbot_type": "consultant",
        "user_id": 1,
        "question": question,
        "store": _STORE,
        "context": {"market": market},
    }


def _state_without_context(question: str = "우리 카페 어떻게 홍보하면 좋을까요?") -> dict:
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
def test_includes_market_data_when_available(mock_call_llm) -> None:
    mock_call_llm.return_value = "전략"

    strategy(_state(market=_MARKET))

    _, user_prompt = mock_call_llm.call_args.args
    assert "43" in user_prompt
    assert "12" in user_prompt
    assert "55" in user_prompt
    assert "높음" in user_prompt
    assert "편의점" in user_prompt


@patch("models.consult.nodes.strategy.call_llm")
def test_omits_market_section_when_market_is_none(mock_call_llm) -> None:
    mock_call_llm.return_value = "전략"

    strategy(_state(market=None))

    _, user_prompt = mock_call_llm.call_args.args
    assert "상권 데이터" not in user_prompt


@patch("models.consult.nodes.strategy.call_llm")
def test_omits_market_section_when_context_missing_entirely(mock_call_llm) -> None:
    """market_for_consult가 아직 안 돈 상태(그래프 조기 실행 등)에서도 죽지 않는다."""
    mock_call_llm.return_value = "전략"

    strategy(_state_without_context())

    _, user_prompt = mock_call_llm.call_args.args
    assert "상권 데이터" not in user_prompt


@patch("models.consult.nodes.strategy.call_llm")
def test_handles_none_nearest_distance_gracefully(mock_call_llm) -> None:
    """동일 업종이 0곳이면 nearest_distance_m이 None인데, 이 경우도 죽지 않고 포맷된다."""
    mock_call_llm.return_value = "전략"
    market = {**_MARKET, "same_industry_count": 0, "nearest_distance_m": None, "density_tier": "경쟁 없음"}

    strategy(_state(market=market))

    _, user_prompt = mock_call_llm.call_args.args
    assert "상권 데이터" in user_prompt


@patch("models.consult.nodes.strategy.call_llm")
def test_handles_missing_market_fields_gracefully(mock_call_llm) -> None:
    """total_count/same_industry_count/density_tier가 누락돼도 KeyError 없이 '정보 없음'/'판단 불가'로 정규화한다."""
    mock_call_llm.return_value = "전략"

    strategy(_state(market={"nearest_distance_m": 55}))

    _, user_prompt = mock_call_llm.call_args.args
    assert "상권 데이터" in user_prompt
    assert "정보 없음" in user_prompt
    assert "판단 불가" in user_prompt


@patch("models.consult.nodes.strategy.call_llm")
def test_formats_none_same_industry_count_as_no_info(mock_call_llm) -> None:
    """same_industry_count가 None이면 'None곳'이 아니라 '정보 없음'으로 표기한다."""
    mock_call_llm.return_value = "전략"
    market = {**_MARKET, "same_industry_count": None}

    strategy(_state(market=market))

    _, user_prompt = mock_call_llm.call_args.args
    assert "None곳" not in user_prompt
    assert "정보 없음" in user_prompt


def test_system_prompt_includes_good_bad_example() -> None:
    """few-shot 예시(SDP §6.4 좋은/나쁜 전략)가 시스템 프롬프트에 포함돼 있다."""
    from models.consult.prompts.strategy import SYSTEM_PROMPT

    assert "나쁜" in SYSTEM_PROMPT
    assert "좋은" in SYSTEM_PROMPT


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
