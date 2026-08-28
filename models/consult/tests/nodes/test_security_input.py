# models/consult/nodes/security_input.py 테스트
from unittest.mock import patch

from models.consult.nodes.security_input import security_input

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


@patch("models.consult.nodes.security_input.check_input")
def test_calls_check_input_with_question(mock_check_input) -> None:
    mock_check_input.return_value = {"action": "pass", "message": ""}

    security_input(_state("우리 카페 어떻게 홍보하면 좋을까요?"))

    mock_check_input.assert_called_once_with("우리 카페 어떻게 홍보하면 좋을까요?")


@patch("models.consult.nodes.security_input.check_input")
def test_stores_result_under_validation_input(mock_check_input) -> None:
    mock_check_input.return_value = {"action": "block", "message": "위험한 입력입니다."}

    result = security_input(_state())

    assert result["validation"] == {"input": {"action": "block", "message": "위험한 입력입니다."}}


@patch("models.consult.nodes.security_input.check_input")
def test_block_stops_pipeline_with_policy_issue(mock_check_input) -> None:
    mock_check_input.return_value = {"action": "block", "message": "위험한 입력입니다."}

    result = security_input(_state())

    assert result["status"] == "blocked"
    assert result["issues"] == [
        {
            "source": "input",
            "action": "block",
            "reason": "illegal_or_injection",
            "message": "위험한 입력입니다.",
        }
    ]


@patch("models.consult.nodes.security_input.check_input")
def test_warn_stops_pipeline_with_reask_issue(mock_check_input) -> None:
    mock_check_input.return_value = {"action": "warn", "message": "질문을 구체적으로 알려주세요."}

    result = security_input(_state())

    assert result["status"] == "blocked"
    assert result["issues"] == [
        {
            "source": "input",
            "action": "reask",
            "reason": "need_clarification",
            "message": "질문을 구체적으로 알려주세요.",
        }
    ]


@patch("models.consult.nodes.security_input.time.monotonic", return_value=1000.0)
@patch("models.consult.nodes.security_input.check_input")
def test_sets_deadline_using_llm_deadline_seconds(mock_check_input, mock_monotonic) -> None:
    """그래프 진입 시 1회 절대 마감을 세팅한다 — 이후 노드들이 이 값을 공유해 call_llm에
    넘기면, 매 호출이 새 예산을 받는 대신 그래프 전체가 하나의 예산을 쓴다(PM 리뷰, PR #93)."""
    from models.shared.config import LLM_DEADLINE_SECONDS

    mock_check_input.return_value = {"action": "pass", "message": ""}

    result = security_input(_state())

    assert result["deadline"] == 1000.0 + LLM_DEADLINE_SECONDS
