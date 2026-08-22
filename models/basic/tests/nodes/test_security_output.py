from unittest.mock import patch

from models.basic.nodes.security_output import security_output_node


@patch("models.basic.nodes.security_output.check_output")
def test_pass_case_joins_only_successful_copies(mock_check_output):
    mock_check_output.return_value = {"action": "pass", "message": ""}
    state = {
        "ranked_copies": [
            {"copy": "여름 신메뉴 카피1"},
            {"copy": "여름 신메뉴 카피2"},
            {
                "copy": None,
                "error": {"field": "copy", "reason": "parse_failed", "message": "실패"},
            },
        ],
        "validation": {},
        "issues": [],
    }

    result = security_output_node(state)

    assert result["validation"]["output"]["action"] == "pass"
    assert "status" not in result
    mock_check_output.assert_called_once_with("여름 신메뉴 카피1\n여름 신메뉴 카피2")


@patch("models.basic.nodes.security_output.check_output")
def test_block_case_sets_blocked_status_and_issue(mock_check_output):
    mock_check_output.return_value = {
        "action": "block",
        "message": "민감정보가 포함되어 있습니다.",
    }
    state = {
        "ranked_copies": [{"copy": "010-1234-5678로 연락주세요"}],
        "validation": {},
        "issues": [],
    }

    result = security_output_node(state)

    assert result["status"] == "blocked"
    assert result["issues"][0]["reason"] == "output_blocked"
