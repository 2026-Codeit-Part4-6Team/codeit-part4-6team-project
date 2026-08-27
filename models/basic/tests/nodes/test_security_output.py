from unittest.mock import patch

from models.basic.nodes.security_output import security_output_node


@patch("models.basic.nodes.security_output.check_output")
def test_pass_case_calls_check_output_per_copy(mock_check_output):
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

    assert result["validation"]["output"] == [
        {"action": "pass", "message": ""},
        {"action": "pass", "message": ""},
    ]
    assert "status" not in result
    assert mock_check_output.call_count == 2
    mock_check_output.assert_any_call("여름 신메뉴 카피1")
    mock_check_output.assert_any_call("여름 신메뉴 카피2")


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
def test_warn_case_masks_only_the_flagged_copy(mock_check_output):
    """카피 내부에 줄바꿈(해시태그 등)이 있어도 카피별로 독립 검사하므로
    마스킹 대상이 밀리지 않는다 — join/split 방식이었을 때 실제로 깨졌던 케이스."""

    def fake_check_output(text):
        if "010-1234-5678" in text:
            return {
                "action": "warn",
                "message": "연락처로 보이는 정보를 가렸습니다. 필요하면 직접 수정해 주세요.",
                "masked_text": "010-****-****로 연락주세요\n#해시태그도포함",
            }
        return {"action": "pass", "message": ""}

    mock_check_output.side_effect = fake_check_output
    state = {
        "ranked_copies": [
            {"copy": "010-1234-5678로 연락주세요\n#연락처공유"},
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
                {
                    "copy": "010-1234-5678로 연락주세요\n#연락처공유",
                    "image_b64": "img1",
                },
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

    assert result["validation"]["output"] == [
        {
            "action": "warn",
            "message": "연락처로 보이는 정보를 가렸습니다. 필요하면 직접 수정해 주세요.",
            "masked_text": "010-****-****로 연락주세요\n#해시태그도포함",
        },
        {"action": "pass", "message": ""},
    ]
    assert "status" not in result
    proposals = result["result"]["proposals"]
    assert proposals[0]["copy"] == "010-****-****로 연락주세요\n#해시태그도포함"
    assert proposals[0]["image_b64"] == "img1"  # 다른 필드는 유지
    assert proposals[1]["copy"] == "두번째 카피"  # pass는 원문 유지
    assert proposals[2]["copy"] is None  # copy 없던 항목은 그대로
