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

    assert result == {"validation": {"input": {"action": "block", "message": "위험한 입력입니다."}}}
