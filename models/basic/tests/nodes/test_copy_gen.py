import json
from unittest.mock import patch

import httpx
import openai

from models.basic.nodes.copy_gen import copy_gen_node

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
        "platform": "instagram",
        "store": _STORE,
        "extra": {},
        "context": {"market": None, "trend": None, "benchmark": None},
        "validation": {},
        "tokens_used": 0,
    }
    return {**base, **overrides}


@patch("models.basic.nodes.copy_gen.call_llm")
def test_three_candidates_are_all_populated(mock_call_llm):
    mock_call_llm.return_value = (
        json.dumps({"candidates": ["카피1", "카피2", "카피3"]}),
        15,
    )

    result = copy_gen_node(_state())

    assert [c["copy"] for c in result["copy_candidates"]] == ["카피1", "카피2", "카피3"]
    assert result["tokens_used"] == 15
    assert "retry_count" not in result


@patch("models.basic.nodes.copy_gen.call_llm")
def test_fewer_than_three_candidates_fills_remainder_with_parse_error(mock_call_llm):
    mock_call_llm.return_value = (json.dumps({"candidates": ["카피1", "카피2"]}), 10)

    result = copy_gen_node(_state())

    candidates = result["copy_candidates"]
    assert candidates[0]["copy"] == "카피1"
    assert candidates[1]["copy"] == "카피2"
    assert candidates[2]["copy"] is None
    assert candidates[2]["error"]["reason"] == "parse_failed"


@patch("models.basic.nodes.copy_gen.call_llm")
def test_all_candidates_failing_increments_retry_without_status_below_max(
    mock_call_llm,
):
    mock_call_llm.return_value = (json.dumps({"candidates": []}), 5)

    result = copy_gen_node(_state(copy_retry_count=0))

    assert all(c["copy"] is None for c in result["copy_candidates"])
    assert result["copy_retry_count"] == 1
    assert "status" not in result


@patch("models.basic.nodes.copy_gen.call_llm")
def test_all_candidates_failing_at_max_retry_sets_error_status(mock_call_llm):
    mock_call_llm.return_value = (json.dumps({"candidates": []}), 5)

    result = copy_gen_node(_state(copy_retry_count=1, issues=[]))

    assert result["copy_retry_count"] == 2
    assert result["status"] == "error"
    assert result["issues"][0]["source"] == "copy_gen"


@patch("models.basic.nodes.copy_gen.call_llm")
def test_regulation_block_message_is_passed_as_avoid_hint(mock_call_llm):
    mock_call_llm.return_value = (
        json.dumps({"candidates": ["카피1", "카피2", "카피3"]}),
        10,
    )

    copy_gen_node(
        _state(
            validation={
                "regulation": {"action": "block", "message": "과장 광고 표현입니다."}
            }
        )
    )

    sent_payload = json.loads(mock_call_llm.call_args.args[1])
    assert sent_payload["avoid"] == "과장 광고 표현입니다."


@patch("models.basic.nodes.copy_gen.call_llm")
def test_call_llm_exception_sets_error_status_with_classified_reason(mock_call_llm):
    mock_call_llm.side_effect = _rate_limit_error()

    result = copy_gen_node(_state(issues=[]))

    assert result["status"] == "error"
    assert result["issues"][0]["source"] == "copy_gen"
    assert result["issues"][0]["reason"] == "rate_limit"


@patch("models.basic.nodes.copy_gen.call_llm")
def test_source_context_strategy_and_reasons_are_passed_to_prompt(mock_call_llm):
    mock_call_llm.return_value = (
        json.dumps({"candidates": ["카피1", "카피2", "카피3"]}),
        10,
    )
    source_context = {
        "generation_id": 7,
        "strategy": {
            "summary": "점심 직장인 타깃",
            "actions": [{"type": "menu", "content": "런치 세트 2종 출시"}],
        },
        "reasons": ["동일 상권 객단가 평균 대비 12% 낮음"],
        "sources": ["상권분석"],
    }

    copy_gen_node(_state(source_context=source_context))

    sent_payload = json.loads(mock_call_llm.call_args.args[1])
    assert sent_payload["consultant_strategy"] == source_context["strategy"]
    assert sent_payload["consultant_reasons"] == source_context["reasons"]


@patch("models.basic.nodes.copy_gen.call_llm")
def test_source_context_sources_are_merged_into_updates(mock_call_llm):
    mock_call_llm.return_value = (
        json.dumps({"candidates": ["카피1", "카피2", "카피3"]}),
        10,
    )
    source_context = {
        "generation_id": 7,
        "strategy": {"summary": "요약", "actions": []},
        "reasons": ["근거"],
        "sources": ["상권분석", "트렌드"],
    }

    result = copy_gen_node(_state(source_context=source_context))

    assert result["sources"] == ["상권분석", "트렌드"]


@patch("models.basic.nodes.copy_gen.call_llm")
def test_no_source_context_omits_consultant_fields_and_sources(mock_call_llm):
    mock_call_llm.return_value = (
        json.dumps({"candidates": ["카피1", "카피2", "카피3"]}),
        10,
    )

    result = copy_gen_node(_state())

    sent_payload = json.loads(mock_call_llm.call_args.args[1])
    assert "consultant_strategy" not in sent_payload
    assert "consultant_reasons" not in sent_payload
    assert "sources" not in result


@patch("models.basic.nodes.copy_gen.call_llm")
def test_seasonality_included_in_payload(mock_call_llm):
    mock_call_llm.return_value = (
        '{"candidates": ["카피1", "카피2", "카피3"]}',
        10,
    )
    state = {
        "question": "여름 신메뉴 홍보",
        "platform": "instagram",
        "store": _STORE,
        "context": {"seasonality": {"reference_date": "2026-08-24", "calendar_period": "8월 하순", "season_hint": "여름 말기"}},
    }

    copy_gen_node(state)

    payload = json.loads(mock_call_llm.call_args.args[1])
    assert payload["seasonality"]["season_hint"] == "여름 말기"