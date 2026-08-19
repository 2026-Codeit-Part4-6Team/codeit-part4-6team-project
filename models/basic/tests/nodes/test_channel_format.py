from models.basic.nodes.channel_format import channel_format_node


def test_full_context_builds_sources_and_truncates_title_to_30_chars():
    question = "여름 신메뉴 홍보 문구 만들어줘 (이건 30자 넘는 긴 질문이라 잘려야 함)"
    state = {
        "question": question,
        "ranked_copies": [
            {"copy": "카피1", "image_b64": "base64data1"},
            {"copy": "카피2", "image_b64": "base64data2"},
            {"copy": "카피3", "image_b64": "base64data3"},
        ],
        "context": {
            "market": "상권 요약",
            "trend": "트렌드 요약",
            "benchmark": "벤치마크 요약",
        },
    }

    result = channel_format_node(state)

    assert result["sources"] == ["상권분석", "트렌드", "벤치마크"]
    assert result["result"]["title"] == question[:30]
    assert len(result["result"]["proposals"]) == 3


def test_empty_context_yields_no_sources():
    state = {
        "question": "짧은 질문",
        "ranked_copies": [{"copy": "카피1", "image_b64": None}],
        "context": {},
    }

    result = channel_format_node(state)

    assert result["sources"] == []


def test_error_field_only_attached_to_failed_proposal():
    error = {"field": "copy", "reason": "parse_failed", "message": "실패"}
    state = {
        "question": "부분 실패 테스트",
        "ranked_copies": [
            {"copy": "카피1", "image_b64": "base64data"},
            {"copy": None, "image_b64": None, "error": error},
        ],
        "context": {"market": "상권 요약"},
    }

    result = channel_format_node(state)

    proposals = result["result"]["proposals"]
    assert "error" not in proposals[0]
    assert proposals[1]["error"] == error


def test_missing_image_b64_key_defaults_to_none_without_keyerror():
    state = {
        "question": "이미지 키 없음 테스트",
        "ranked_copies": [{"copy": "카피1"}],
        "context": {},
    }

    result = channel_format_node(state)

    assert result["result"]["proposals"][0]["image_b64"] is None
