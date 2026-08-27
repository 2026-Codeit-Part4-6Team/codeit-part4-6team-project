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
        "message": "카피 생성에 실패해 규제 검사를 진행할 수 없습니다.",
        "alternative": "",
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


@patch("models.basic.nodes.regulation_node.check_regulation")
def test_passed_copy_does_not_leak_internal_regulation_key(mock_check_regulation):
    mock_check_regulation.return_value = {
        "action": "pass",
        "law": "",
        "reason": "",
        "alternative": "",
        "message": "",
    }
    state = {
        "ranked_copies": [{"copy": "정상 카피", "score": 4.5}],
        "validation": {},
        "issues": [],
    }

    result = regulation_node(state)

    assert "regulation" not in result["ranked_copies"][0]


@patch("models.basic.nodes.regulation_node.check_regulation")
def test_middle_item_blocked_stays_in_original_rank_position(mock_check_regulation):
    """차단된 항목이 배열 끝으로 밀리지 않고 원래 순위 자리를 유지해야 한다
    (사용자에게 점수순 A·B·C가 아니라 A·C·B로 보이는 버그 회귀 방지)."""
    mock_check_regulation.side_effect = [
        {"action": "pass", "law": "", "reason": "", "alternative": "", "message": ""},
        {
            "action": "block",
            "reason": "exaggeration",
            "message": "과장 광고 표현입니다.",
        },
        {"action": "pass", "law": "", "reason": "", "alternative": "", "message": ""},
    ]
    state = {
        "ranked_copies": [
            {"copy": "A", "score": 4.8},
            {"copy": "B", "score": 4.2},
            {"copy": "C", "score": 3.9},
        ],
        "validation": {},
        "issues": [],
    }

    result = regulation_node(state)

    assert [c["copy"] for c in result["ranked_copies"]] == ["A", None, "C"]
    assert result["ranked_copies"][1]["error"]["reason"] == "content_policy"


@patch("models.basic.nodes.regulation_node.check_regulation")
def test_blocked_at_retry_cap_with_empty_message_falls_back_to_default(
    mock_check_regulation,
):
    """check_regulation이 빈 메시지를 주더라도 blocked 응답의 message는
    빈 문자열이면 안 된다(D-215, BlockedResult.message min_length=1)."""
    mock_check_regulation.return_value = {
        "action": "block",
        "reason": "exaggeration",
        "message": "",
    }
    state = {
        "ranked_copies": [{"copy": "최고의 카페 코드잇!", "score": 4.5}],
        "validation": {},
        "copy_retry_count": 1,
        "issues": [],
    }

    result = regulation_node(state)

    assert result["status"] == "blocked"
    assert result["issues"][0]["message"] == "요청을 처리할 수 없습니다."
