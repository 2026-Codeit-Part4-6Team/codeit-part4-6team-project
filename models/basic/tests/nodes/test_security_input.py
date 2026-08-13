from unittest.mock import patch

from models.basic.nodes.security_input import security_input_node


def _state(**overrides):
    base = {
        "question": "여름 신메뉴 홍보 문구 만들어줘",
        "validation": {},
        "issues": [],
    }
    return {**base, **overrides}


@patch("models.basic.nodes.security_input.check_input")
def test_pass_updates_validation_without_blocking(mock_check_input):
    mock_check_input.return_value = {"action": "pass", "message": ""}

    result = security_input_node(_state())

    assert result["validation"]["input"]["action"] == "pass"
    assert "status" not in result
    mock_check_input.assert_called_once_with("여름 신메뉴 홍보 문구 만들어줘")


@patch("models.basic.nodes.security_input.check_input")
def test_block_sets_blocked_status_and_issue(mock_check_input):
    mock_check_input.return_value = {
        "action": "block",
        "message": "불법 키워드가 포함되어 있습니다.",
    }

    result = security_input_node(_state(question="마약 광고 만들어줘"))

    assert result["status"] == "blocked"
    assert result["issues"][0] == {
        "source": "input",
        "action": "block",
        "reason": "input_blocked",
        "message": "불법 키워드가 포함되어 있습니다.",
    }
