# models/consult/nodes/self_check_node.py 테스트
import logging
from unittest.mock import patch

from models.consult.nodes.self_check_node import self_check_node

_STORE = {
    "name": "카페 코드잇",
    "type": "카페",
    "address": "서울 강남구 역삼동",
    "lat": 37.5,
    "lng": 127.0,
}


def _state(*, result: dict | None = None, context: dict | None = None) -> dict:
    state = {
        "chatbot_type": "consultant",
        "user_id": 1,
        "question": "질문",
        "store": _STORE,
    }
    if result is not None:
        state["result"] = result
    if context is not None:
        state["context"] = context
    return state


@patch("models.consult.nodes.self_check_node.self_check")
def test_calls_self_check_with_result_and_context(mock_self_check) -> None:
    mock_self_check.return_value = {"action": "pass", "reasons": [], "message": ""}
    result = {"summary": "전략 요약"}
    context = {"market": {"density_tier": "높음"}}

    self_check_node(_state(result=result, context=context))

    mock_self_check.assert_called_once_with(result, context)


@patch("models.consult.nodes.self_check_node.self_check")
def test_stores_result_under_validation_self_check(mock_self_check) -> None:
    mock_self_check.return_value = {"action": "reject", "reasons": ["근거 없음"], "message": ""}

    result = self_check_node(_state())

    assert result["validation"] == {
        "self_check": {"action": "reject", "reasons": ["근거 없음"], "message": ""}
    }


@patch("models.consult.nodes.self_check_node.self_check")
def test_warn_logs_and_does_not_block(mock_self_check, caplog) -> None:
    mock_self_check.return_value = {
        "action": "warn",
        "reasons": ["근거 개수 부족"],
        "message": "근거가 약합니다.",
    }

    with caplog.at_level(logging.WARNING):
        result = self_check_node(_state())

    assert "status" not in result
    assert "근거 개수 부족" in caplog.text


@patch("models.consult.nodes.self_check_node.self_check")
def test_first_reject_requests_one_strategy_retry(mock_self_check) -> None:
    mock_self_check.return_value = {
        "action": "reject",
        "reasons": ["답변 근거 없음"],
        "message": "답변 근거가 부족합니다.",
    }

    result = self_check_node(_state())

    assert result["self_check_retry_count"] == 1
    assert "status" not in result


@patch("models.consult.nodes.self_check_node.self_check")
def test_repeated_reject_returns_contract_safe_error(mock_self_check) -> None:
    mock_self_check.return_value = {
        "action": "reject",
        "reasons": ["답변 근거 없음"],
        "message": "답변 근거가 부족합니다.",
    }
    state = _state()
    state["self_check_retry_count"] = 1

    result = self_check_node(state)

    assert result["status"] == "error"
    assert result["issues"] == [
        {
            "source": "self_check",
            "action": "reject",
            "reason": "unknown",
            "message": "답변 근거가 부족합니다.",
        }
    ]


@patch("models.consult.nodes.self_check_node.self_check")
def test_handles_missing_result_and_context_gracefully(mock_self_check) -> None:
    """result·context가 아직 안 채워진 상태에서도 빈 dict로 안전하게 호출한다."""
    mock_self_check.return_value = {"action": "pass", "reasons": [], "message": ""}
    state = _state()
    assert "result" not in state
    assert "context" not in state

    self_check_node(state)

    mock_self_check.assert_called_once_with({}, {})


def test_passes_top_level_sources_to_real_self_check() -> None:
    state = _state(
        result={
            "summary": "상권 현황을 반영해 대표 메뉴와 재방문 프로모션을 함께 운영하세요.",
            "actions": [
                {"type": "menu", "content": "대표 메뉴 구성을 정리하세요."},
                {"type": "promotion", "content": "재방문 프로모션을 운영하세요."},
            ],
            "reasons": ["반경 내 동일 업종 매장 수를 근거로 활용했습니다."],
        },
        context={"market": {"same_industry_count": 12}},
    )
    state["sources"] = ["상권분석"]

    result = self_check_node(state)

    assert result["validation"]["self_check"]["action"] == "pass"
