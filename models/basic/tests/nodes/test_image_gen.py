from unittest.mock import patch

import httpx
import openai

from models.basic.nodes.image_gen import image_gen_node

_STORE = {"name": "카페 코드잇", "type": "카페", "lat": 37.5, "lng": 127.0}


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
    assert all("image_prompt" in c for c in result["ranked_copies"])
    assert result["image_results"] == [
        "base64imagedata",
        "base64imagedata",
        "base64imagedata",
    ]
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
def test_prompt_includes_store_type_and_copy_text_and_is_saved_as_image_prompt(
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
    assert result["ranked_copies"][0]["image_prompt"] == prompt


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
    assert first["image_prompt"]
    assert second["image_b64"] is None
    assert second["error"]["field"] == "image"
    assert second["error"]["reason"] == "rate_limit"
    assert "image_prompt" not in second
    assert third["image_b64"] == "base64imagedata"
    assert third["image_prompt"]
    assert result["image_results"] == ["base64imagedata", "base64imagedata"]
