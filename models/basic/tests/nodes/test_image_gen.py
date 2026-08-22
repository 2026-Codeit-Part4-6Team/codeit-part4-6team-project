import base64
from unittest.mock import patch

import httpx
import openai

from models.basic.nodes.image_gen import image_gen_node

_STORE = {"name": "카페 코드잇", "type": "카페", "lat": 37.5, "lng": 127.0}


def _fake_png_b64() -> str:
    """Image.open()으로 디코딩 가능한 1x1 투명 PNG."""
    return base64.b64encode(
        bytes.fromhex(
            "89504e470d0a1a0a0000000d4948445200000001000000010806000000"
            "1f15c4890000000a49444154789c63000100000500010d0a2db400000000"
            "49454e44ae426082"
        )
    ).decode()


def _rate_limit_error() -> openai.RateLimitError:
    request = httpx.Request("POST", "https://api.openai.com/v1/images/generations")
    response = httpx.Response(status_code=429, request=request)
    return openai.RateLimitError("rate limited", response=response, body=None)


@patch("models.basic.nodes.image_gen.generate_image")
def test_successful_generation_attaches_image_b64_to_each_valid_copy(
    mock_generate_image,
):
    mock_generate_image.return_value = "base64imagedata"
    state = {
        "store": _STORE,
        "ranked_copies": [
            {"copy": "카피1", "score": 4.5},
            {"copy": "카피2", "score": 4.0},
            {"copy": "카피3", "score": 3.8},
        ],
    }

    result = image_gen_node(state)

    assert [c["image_b64"] for c in result["ranked_copies"]] == [
        "base64imagedata",
        "base64imagedata",
        "base64imagedata",
    ]
    assert all("image_prompt" not in c for c in result["ranked_copies"])
    assert result["image_results"] == [
        "base64imagedata",
        "base64imagedata",
        "base64imagedata",
    ]
    assert len(result["image_prompts"]) == 3
    assert all(result["image_prompts"])
    assert mock_generate_image.call_count == 3


@patch("models.basic.nodes.image_gen.generate_image")
def test_copy_less_item_is_skipped_without_calling_generate_image(mock_generate_image):
    mock_generate_image.return_value = "base64imagedata"
    failed = {
        "copy": None,
        "error": {"field": "copy", "reason": "parse_failed", "message": "실패"},
    }
    state = {
        "store": _STORE,
        "ranked_copies": [
            {"copy": "카피1", "score": 4.5},
            {"copy": "카피2", "score": 4.0},
            failed,
        ],
    }

    result = image_gen_node(state)

    assert result["ranked_copies"][2] == failed
    assert result["ranked_copies"][0]["image_b64"] == "base64imagedata"
    assert result["ranked_copies"][1]["image_b64"] == "base64imagedata"
    assert result["image_results"] == ["base64imagedata", "base64imagedata"]
    assert mock_generate_image.call_count == 2


@patch("models.basic.nodes.image_gen.generate_image")
def test_prompt_includes_store_type_and_copy_text_and_is_saved_in_image_prompts(
    mock_generate_image,
):
    mock_generate_image.return_value = "base64imagedata"
    state = {
        "store": _STORE,
        "ranked_copies": [{"copy": "여름 신메뉴", "score": 4.5}],
    }

    result = image_gen_node(state)

    prompt = mock_generate_image.call_args.args[0]
    assert "카페" in prompt
    assert "여름 신메뉴" in prompt
    assert "image_prompt" not in result["ranked_copies"][0]
    assert result["image_prompts"] == [prompt]


@patch("models.basic.nodes.image_gen.generate_image")
def test_generation_failure_records_classified_error_and_keeps_batch_going(
    mock_generate_image,
):
    mock_generate_image.side_effect = [
        "base64imagedata",
        _rate_limit_error(),
        "base64imagedata",
    ]
    state = {
        "store": _STORE,
        "ranked_copies": [
            {"copy": "카피1", "score": 4.5},
            {"copy": "카피2", "score": 4.0},
            {"copy": "카피3", "score": 3.8},
        ],
    }

    result = image_gen_node(state)

    first, second, third = result["ranked_copies"]
    assert first["image_b64"] == "base64imagedata"
    assert "image_prompt" not in first
    assert second["image_b64"] is None
    assert second["error"]["field"] == "image"
    assert second["error"]["reason"] == "rate_limit"
    assert "image_prompt" not in second
    assert third["image_b64"] == "base64imagedata"
    assert "image_prompt" not in third
    assert result["image_results"] == ["base64imagedata", "base64imagedata"]
    assert len(result["image_prompts"]) == 3
    assert result["image_prompts"][0]
    assert result["image_prompts"][1] is None
    assert result["image_prompts"][2]


@patch("models.basic.nodes.image_gen.call_llm")
@patch("models.basic.nodes.image_gen.generate_image")
def test_prompts_and_captions_stay_aligned_when_middle_item_has_no_copy(
    mock_generate_image, mock_call_llm
):
    """카피 없는 항목이 중간에 섞여도 image_prompts/image_captions_en이
    ranked_copies와 같은 인덱스를 유지해야 한다(정렬 버그 회귀 방지)."""
    mock_generate_image.return_value = "base64imagedata"
    mock_call_llm.return_value = ("An iced coffee ad photo", 5)
    failed = {
        "copy": None,
        "error": {"field": "copy", "reason": "parse_failed", "message": "실패"},
    }
    state = {
        "store": _STORE,
        "ranked_copies": [
            {"copy": "카피1", "score": 4.5},
            failed,
            {"copy": "카피3", "score": 3.8},
        ],
    }

    result = image_gen_node(state)

    assert len(result["image_prompts"]) == 3
    assert len(result["image_captions_en"]) == 3
    assert result["image_prompts"][1] is None
    assert result["image_captions_en"][1] is None
    assert result["image_prompts"][0] is not None
    assert result["image_prompts"][2] is not None
    assert result["image_captions_en"][0] == "An iced coffee ad photo"
    assert result["image_captions_en"][2] == "An iced coffee ad photo"


@patch("models.basic.nodes.image_gen.call_llm")
@patch("models.basic.nodes.image_gen.generate_image")
def test_caption_generation_failure_does_not_block_image_generation(
    mock_generate_image, mock_call_llm
):
    """영문 캡션 생성이 실패해도 이미지 생성 자체는 성공해야 한다."""
    mock_generate_image.return_value = "base64imagedata"
    mock_call_llm.side_effect = RuntimeError("번역 실패")
    state = {
        "store": _STORE,
        "ranked_copies": [{"copy": "카피1", "score": 4.5}],
    }

    result = image_gen_node(state)

    assert result["ranked_copies"][0]["image_b64"] == "base64imagedata"
    assert result["image_captions_en"][0] is None


@patch("models.basic.nodes.image_gen.generate_image")
def test_instagram_platform_uses_square_size_and_style(mock_generate_image):
    mock_generate_image.return_value = "base64imagedata"
    state = {
        "store": _STORE,
        "platform": "instagram",
        "ranked_copies": [{"copy": "여름 신메뉴", "score": 4.5}],
    }

    image_gen_node(state)

    prompt = mock_generate_image.call_args.args[0]
    assert mock_generate_image.call_args.kwargs["size"] == "1024x1024"
    assert "라이프스타일" in prompt


@patch("models.basic.nodes.image_gen.generate_image")
def test_xbanner_platform_generates_top_and_bottom_then_stacks(mock_generate_image):
    mock_generate_image.return_value = _fake_png_b64()
    state = {
        "store": _STORE,
        "platform": "xbanner",
        "ranked_copies": [{"copy": "여름 신메뉴", "score": 4.5}],
    }

    result = image_gen_node(state)

    assert mock_generate_image.call_count == 2
    calls = mock_generate_image.call_args_list
    top_prompt = calls[0].args[0]
    bottom_prompt = calls[1].args[0]
    assert calls[0].kwargs["size"] == "1024x1536"
    assert calls[1].kwargs["size"] == "1024x1536"
    assert "여름 신메뉴" in top_prompt
    assert "카페 코드잇" in bottom_prompt
    assert "다른 브랜드명" in bottom_prompt
    assert result["ranked_copies"][0]["image_b64"] is not None
    assert result["image_captions_en"] == [None]


@patch("models.basic.nodes.image_gen.generate_image")
def test_xbanner_generation_failure_records_error_without_crashing(mock_generate_image):
    mock_generate_image.side_effect = _rate_limit_error()
    state = {
        "store": _STORE,
        "platform": "xbanner",
        "ranked_copies": [{"copy": "여름 신메뉴", "score": 4.5}],
    }

    result = image_gen_node(state)

    item = result["ranked_copies"][0]
    assert item["image_b64"] is None
    assert item["error"]["field"] == "image"
    assert item["error"]["reason"] == "rate_limit"


@patch("models.basic.nodes.image_gen.generate_image")
def test_missing_platform_falls_back_to_instagram_default(mock_generate_image):
    mock_generate_image.return_value = "base64imagedata"
    state = {
        "store": _STORE,
        "ranked_copies": [{"copy": "여름 신메뉴", "score": 4.5}],
    }

    image_gen_node(state)

    assert mock_generate_image.call_args.kwargs["size"] == "1024x1024"
