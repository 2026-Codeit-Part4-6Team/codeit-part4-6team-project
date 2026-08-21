import base64

import pytest

from backend.services.generation_service import (
    ApprovedImageInvalid,
    ApprovedImageTooLarge,
    canonicalize_approved_image,
)

PNG = b"\x89PNG\r\n\x1a\n" + b"payload"
JPEG = b"\xff\xd8\xff" + b"payload"
WEBP = b"RIFF" + (4).to_bytes(4, "little") + b"WEBP" + b"payload"


@pytest.mark.parametrize(
    ("data", "mime"),
    [(PNG, "image/png"), (JPEG, "image/jpeg"), (WEBP, "image/webp")],
)
def test_raw_and_data_uri_images_share_one_canonical_value(data, mime):
    raw = base64.b64encode(data).decode()
    expected = f"data:{mime};base64,{raw}"

    assert canonicalize_approved_image(raw, max_image_bytes=100) == expected
    assert (
        canonicalize_approved_image(
            f"data:{mime};base64,{raw}", max_image_bytes=100
        )
        == expected
    )


@pytest.mark.parametrize(
    "value",
    [
        "not-base64",
        "data:text/plain;base64,SGVsbG8=",
        "data:image/png,not-base64",
        "data:image/jpeg;base64,iVBORw0KGgpheWxvYWQ=",
        base64.b64encode(b"unknown-format").decode(),
    ],
)
def test_image_rejects_invalid_encoding_mime_or_signature(value):
    with pytest.raises(ApprovedImageInvalid):
        canonicalize_approved_image(value, max_image_bytes=100)


def test_image_rejects_decoded_bytes_over_limit():
    with pytest.raises(ApprovedImageTooLarge):
        canonicalize_approved_image(
            base64.b64encode(PNG).decode(), max_image_bytes=len(PNG) - 1
        )


def test_none_image_remains_none():
    assert canonicalize_approved_image(None, max_image_bytes=100) is None
