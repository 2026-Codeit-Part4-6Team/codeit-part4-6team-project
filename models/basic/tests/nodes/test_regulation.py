from unittest.mock import patch

from models.basic.nodes.regulation_node import regulation_node


@patch("models.basic.nodes.regulation_node.check_regulation")
def test_all_pass_returns_validated_copies_with_failed_appended(mock_check_regulation):
    mock_check_regulation.return_value = {
        "action": "pass",
        "law": "",
        "reason": "",
        "alternative": "",
        "message": "",
    }
    failed = {
        "copy": None,
        "error": {"field": "copy", "reason": "parse_failed", "message": "실패"},
    }
    state = {
        "ranked_copies": [
            {"copy": "여름 신메뉴 카피1", "score": 4.5},
            {"copy": "여름 신메뉴 카피2", "score": 4.0},
            failed,
        ],
        "validation": {},
        "retry_count": 0,
        "issues": [],
    }

    result = regulation_node(state)

    assert [c["copy"] for c in result["ranked_copies"]] == [
        "여름 신메뉴 카피1",
        "여름 신메뉴 카피2",
        None,
    ]
    assert result["validation"]["regulation"]["action"] == "pass"


@patch("models.basic.nodes.regulation_node.check_regulation")
def test_blocked_below_retry_cap_increments_retry_without_final_status(
    mock_check_regulation,
):
    mock_check_regulation.return_value = {
        "action": "block",
        "reason": "exaggeration",
        "message": "과장 광고 표현입니다.",
    }
    state = {
        "ranked_copies": [{"copy": "최고의 카페 코드잇!", "score": 4.5}],
        "validation": {},
        "copy_retry_count": 0,
        "issues": [],
    }

    result = regulation_node(state)

    assert result["copy_retry_count"] == 1
    assert result["validation"]["regulation"]["action"] == "block"
    assert "status" not in result


@patch("models.basic.nodes.regulation_node.check_regulation")
def test_blocked_at_retry_cap_sets_blocked_status_and_issue(mock_check_regulation):
    mock_check_regulation.return_value = {
        "action": "block",
        "reason": "exaggeration",
        "message": "과장 광고 표현입니다.",
    }
    state = {
        "ranked_copies": [{"copy": "최고의 카페 코드잇!", "score": 4.5}],
        "validation": {},
        "copy_retry_count": 1,
        "issues": [],
    }

    result = regulation_node(state)

    assert result["copy_retry_count"] == 2
    assert result["status"] == "blocked"
    assert result["issues"][0]["reason"] == "exaggeration"


@patch("models.basic.nodes.regulation_node.check_regulation")
def test_no_valid_copies_blocks_without_calling_check_regulation(mock_check_regulation):
    state = {
        "ranked_copies": [
            {
                "copy": None,
                "error": {"field": "copy", "reason": "parse_failed", "message": "실패"},
            }
        ],
        "validation": {},
        "copy_retry_count": 1,
        "issues": [],
    }

    result = regulation_node(state)

    mock_check_regulation.assert_not_called()
    assert result["validation"]["regulation"] == {
        "action": "block",
        "reason": "no_valid_copy",
        "message": "",
    }
    assert result["status"] == "blocked"


@patch("models.basic.nodes.regulation_node.check_regulation")
def test_partial_block_replaces_blocked_copy_with_placeholder_slot(
    mock_check_regulation,
):
    """일부만 차단되면 배열에서 빼지 않고 자리(슬롯)를 유지해야 proposals 개수가 안 깨진다."""
    mock_check_regulation.side_effect = [
        {"action": "pass", "law": "", "reason": "", "alternative": "", "message": ""},
        {
            "action": "block",
            "reason": "exaggeration",
            "message": "과장 광고 표현입니다.",
        },
    ]
    state = {
        "ranked_copies": [
            {"copy": "정상 카피", "score": 4.5},
            {"copy": "최고의 카페!", "score": 4.0},
        ],
        "validation": {},
        "retry_count": 0,
        "issues": [],
    }

    result = regulation_node(state)

    assert len(result["ranked_copies"]) == 2
    assert result["ranked_copies"][0]["copy"] == "정상 카피"
    assert result["ranked_copies"][1] == {
        "copy": None,
        "image_b64": None,
        "error": {
            "field": "copy",
            "reason": "content_policy",
            "message": "과장 광고 표현입니다.",
        },
    }
    assert result["validation"]["regulation"]["action"] == "pass"
