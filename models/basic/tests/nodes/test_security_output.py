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


@patch("models.basic.nodes.security_output.check_output")
def test_warn_case_replaces_masked_copy_in_result_proposals(mock_check_output):
    mock_check_output.return_value = {
        "action": "warn",
        "message": "연락처로 보이는 정보를 가렸습니다. 필요하면 직접 수정해 주세요.",
        "masked_text": "010-****-****로 연락주세요\n두번째 카피",
    }
    state = {
        "ranked_copies": [
            {"copy": "010-1234-5678로 연락주세요"},
            {"copy": "두번째 카피"},
            {
                "copy": None,
                "error": {"field": "copy", "reason": "parse_failed", "message": "실패"},
            },
        ],
        "validation": {},
        "issues": [],
        "result": {
            "title": "제목",
            "proposals": [
                {"copy": "010-1234-5678로 연락주세요", "image_b64": "img1"},
                {"copy": "두번째 카피", "image_b64": "img2"},
                {
                    "copy": None,
                    "error": {
                        "field": "copy",
                        "reason": "parse_failed",
                        "message": "실패",
                    },
                },
            ],
        },
    }

    result = security_output_node(state)

    assert result["validation"]["output"]["action"] == "warn"
    assert "status" not in result
    proposals = result["result"]["proposals"]
    assert proposals[0]["copy"] == "010-****-****로 연락주세요"
    assert proposals[0]["image_b64"] == "img1"  # 다른 필드는 유지
    assert proposals[1]["copy"] == "두번째 카피"
    assert proposals[2]["copy"] is None  # copy 없던 항목은 그대로
