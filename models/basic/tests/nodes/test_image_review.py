import base64
from unittest.mock import patch

from models.basic.nodes.image_review import image_review_node


def _fake_png_b64() -> str:
    # 1x1 투명 PNG
    return base64.b64encode(
        bytes.fromhex(
            "89504e470d0a1a0a0000000d4948445200000001000000010806000000"
            "1f15c4890000000a49444154789c6300010000050001"
            "0d0a2db40000000049454e44ae426082"
        )
    ).decode()


def test_missing_image_does_not_reject():
    state = {
        "ranked_copies": [
            {"copy": "카피1", "image_b64": None},
            {"copy": "카피2", "image_b64": None},
        ],
    }

    result = image_review_node(state)

    assert result["image_review_result"]["action"] == "pass"
    assert "image_retry_count" not in result


def test_decode_failure_on_all_items_rejects_and_increments_image_retry_count():
    state = {
        "ranked_copies": [
            {"copy": "카피1", "image_b64": "이건-base64가-아님"},
        ],
        "image_retry_count": 0,
    }

    result = image_review_node(state)

    assert result["image_review_result"]["action"] == "reject"
    assert result["image_retry_count"] == 1
    assert result["ranked_copies"][0]["error"]["reason"] == "unknown"


def test_partial_decode_failure_still_passes():
    state = {
        "ranked_copies": [
            {"copy": "카피1", "image_b64": None},
            {"copy": "카피2", "image_b64": "이건-base64가-아님"},
        ],
    }

    result = image_review_node(state)

    assert result["image_review_result"]["action"] == "pass"


@patch("models.basic.nodes.image_review._clip_score")
def test_clip_score_uses_matching_image_prompt_by_index(mock_clip_score):
    mock_clip_score.return_value = 0.5
    state = {
        "ranked_copies": [
            {"copy": "카피1", "image_b64": _fake_png_b64()},
            {"copy": "카피2", "image_b64": _fake_png_b64()},
        ],
        "image_prompts": ["카피1용 프롬프트", "카피2용 프롬프트"],
    }

    image_review_node(state)

    calls = [call.args[1] for call in mock_clip_score.call_args_list]
    assert calls == ["카피1용 프롬프트", "카피2용 프롬프트"]


@patch("models.basic.nodes.image_review._clip_score")
def test_clip_score_uses_correct_caption_when_middle_item_has_no_copy(mock_clip_score):
    """카피 없는 항목이 중간에 섞여도 캡션이 올바른 항목과 짝지어져야 한다."""
    mock_clip_score.return_value = 0.5
    failed = {
        "copy": None,
        "error": {"field": "copy", "reason": "parse_failed", "message": "실패"},
    }
    state = {
        "ranked_copies": [
            {"copy": "카피1", "image_b64": _fake_png_b64()},
            failed,
            {"copy": "카피3", "image_b64": _fake_png_b64()},
        ],
        "image_prompts": ["카피1용 한글 프롬프트", None, "카피3용 한글 프롬프트"],
        "image_captions_en": ["caption for copy1", None, "caption for copy3"],
    }

    image_review_node(state)

    calls = [call.args[1] for call in mock_clip_score.call_args_list]
    assert calls == ["caption for copy1", "caption for copy3"]


@patch("models.basic.nodes.image_review._clip_score")
def test_clip_score_prefers_english_caption_over_korean_prompt(mock_clip_score):
    """영문 캡션이 있으면 한글 프롬프트보다 우선해서 CLIP 채점에 써야 한다(P-015)."""
    mock_clip_score.return_value = 0.5
    state = {
        "ranked_copies": [{"copy": "카피1", "image_b64": _fake_png_b64()}],
        "image_prompts": ["카페 광고용 상업 사진"],
        "image_captions_en": ["An iced coffee ad photo"],
    }

    image_review_node(state)

    assert mock_clip_score.call_args.args[1] == "An iced coffee ad photo"
