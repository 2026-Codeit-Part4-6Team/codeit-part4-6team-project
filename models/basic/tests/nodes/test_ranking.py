import json
from unittest.mock import patch

import httpx
import openai

from models.basic.nodes.ranking import ranking_node

_QUESTION = "여름 신메뉴 홍보 문구 만들어줘"


def _rate_limit_error() -> openai.RateLimitError:
    request = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")
    response = httpx.Response(status_code=429, request=request)
    return openai.RateLimitError("rate limited", response=response, body=None)


@patch("models.basic.nodes.ranking.call_llm")
def test_all_valid_candidates_are_ranked_by_llm(mock_call_llm):
    mock_call_llm.return_value = (
        json.dumps(
            {
                "ranked": [
                    {"index": 1, "score": 4.8},
                    {"index": 0, "score": 4.2},
                ]
            }
        ),
        8,
    )
    state = {
        "question": _QUESTION,
        "copy_candidates": [{"copy": "카피A"}, {"copy": "카피B"}],
        "tokens_used": 0,
    }

    result = ranking_node(state)

    assert result["ranked_copies"] == [
        {"copy": "카피B", "score": 4.8},
        {"copy": "카피A", "score": 4.2},
    ]
    assert result["tokens_used"] == 8
    sent_payload = json.loads(mock_call_llm.call_args.args[1])
    assert sent_payload["candidate"] == ["카피A", "카피B"]


@patch("models.basic.nodes.ranking.call_llm")
def test_failed_candidates_bypass_llm_and_are_appended_after_ranked(mock_call_llm):
    failed_candidate = {
        "copy": None,
        "image_b64": None,
        "error": {
            "field": "copy",
            "reason": "parse_failed",
            "message": "카피 생성에 실패했습니다.",
        },
    }
    mock_call_llm.return_value = (
        json.dumps({"ranked": [{"index": 0, "score": 4.5}]}),
        5,
    )
    state = {
        "question": _QUESTION,
        "copy_candidates": [{"copy": "카피A"}, failed_candidate],
        "tokens_used": 0,
    }

    result = ranking_node(state)

    assert result["ranked_copies"] == [
        {"copy": "카피A", "score": 4.5},
        failed_candidate,
    ]
    sent_payload = json.loads(mock_call_llm.call_args.args[1])
    assert sent_payload["candidate"] == ["카피A"]


@patch("models.basic.nodes.ranking.call_llm")
def test_all_candidates_failed_skips_llm_call_entirely(mock_call_llm):
    failed = [
        {
            "copy": None,
            "error": {"field": "copy", "reason": "parse_failed", "message": "실패1"},
        },
        {
            "copy": None,
            "error": {"field": "copy", "reason": "parse_failed", "message": "실패2"},
        },
    ]
    state = {"question": _QUESTION, "copy_candidates": failed, "tokens_used": 0}

    result = ranking_node(state)

    assert result == {"ranked_copies": failed}
    mock_call_llm.assert_not_called()


@patch("models.basic.nodes.ranking.call_llm")
def test_missing_or_invalid_indices_are_backfilled_in_original_order(mock_call_llm):
    """LLM이 index를 일부 빠뜨리거나 범위 밖 값을 줘도 개수가 보장돼야 한다."""
    mock_call_llm.return_value = (
        json.dumps(
            {
                "ranked": [
                    {"index": 5, "score": 9.9},  # 범위 밖 → 무시
                    {"index": 0, "score": 4.0},
                ]
            }
        ),
        3,
    )
    state = {
        "question": _QUESTION,
        "copy_candidates": [{"copy": "카피A"}, {"copy": "카피B"}],
        "tokens_used": 0,
    }

    result = ranking_node(state)

    assert result["ranked_copies"] == [
        {"copy": "카피A", "score": 4.0},
        {"copy": "카피B", "score": None},
    ]


@patch("models.basic.nodes.ranking.call_llm")
def test_call_llm_exception_sets_error_status_with_classified_reason(mock_call_llm):
    mock_call_llm.side_effect = _rate_limit_error()
    state = {
        "question": _QUESTION,
        "copy_candidates": [{"copy": "카피A"}, {"copy": "카피B"}],
        "tokens_used": 0,
        "issues": [],
    }

    result = ranking_node(state)

    assert result["status"] == "error"
    assert result["issues"][0]["source"] == "ranking"
    assert result["issues"][0]["reason"] == "rate_limit"
