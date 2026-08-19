from unittest.mock import patch

from models.basic.nodes.self_check_node import self_check_node


@patch("models.basic.nodes.self_check_node.self_check")
def test_pass_case_records_validation_without_blocking(mock_self_check):
    mock_self_check.return_value = {"action": "pass", "reasons": [], "message": ""}
    state = {
        "result": {
            "title": "여름 신메뉴 홍보",
            "proposals": [
                {"copy": "여름엔 시원한 아이스 아메리카노, 카페 코드잇에서!"},
                {"copy": "카페 코드잇 신메뉴로 더위를 날려보세요"},
            ],
        },
        "context": {"market": "반경 내 동일 업종 3곳"},
        "validation": {},
        "issues": [],
    }

    result = self_check_node(state)

    assert result["validation"]["self_check"]["action"] == "pass"
    assert "status" not in result
    mock_self_check.assert_called_once_with(state["result"], state["context"])


@patch("models.basic.nodes.self_check_node.self_check")
def test_reject_case_sets_blocked_status_and_issue(mock_self_check):
    mock_self_check.return_value = {
        "action": "reject",
        "reasons": ["근거 없음"],
        "message": "생성 근거가 부족합니다.",
    }
    state = {
        "result": {"title": "여름 신메뉴 홍보", "proposals": [{"copy": "카피"}]},
        "context": {},
        "validation": {},
        "issues": [],
    }

    result = self_check_node(state)

    assert result["status"] == "blocked"
    assert result["issues"][0]["message"] == "생성 근거가 부족합니다."
