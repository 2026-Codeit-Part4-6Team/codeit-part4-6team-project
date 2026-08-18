# models/consult/nodes/self_check_node.py 테스트
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

    assert result == {
        "validation": {"self_check": {"action": "reject", "reasons": ["근거 없음"], "message": ""}}
    }


@patch("models.consult.nodes.self_check_node.self_check")
def test_handles_missing_result_and_context_gracefully(mock_self_check) -> None:
    """result·context가 아직 안 채워진 상태에서도 빈 dict로 안전하게 호출한다."""
    mock_self_check.return_value = {"action": "pass", "reasons": [], "message": ""}
    state = _state()
    assert "result" not in state
    assert "context" not in state

    self_check_node(state)

    mock_self_check.assert_called_once_with({}, {})
