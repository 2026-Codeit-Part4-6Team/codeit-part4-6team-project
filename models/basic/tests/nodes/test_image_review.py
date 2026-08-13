import base64

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
    assert result["ranked_copies"][0]["error"]["reason"] == "decode_failed"


def test_partial_decode_failure_still_passes():
    state = {
        "ranked_copies": [
            {"copy": "카피1", "image_b64": None},
            {"copy": "카피2", "image_b64": "이건-base64가-아님"},
        ],
    }

    result = image_review_node(state)

    assert result["image_review_result"]["action"] == "pass"
