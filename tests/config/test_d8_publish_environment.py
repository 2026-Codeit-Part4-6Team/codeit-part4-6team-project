import pytest

from backend.config import load_settings


def test_publish_image_limit_defaults_to_five_megabytes(monkeypatch):
    monkeypatch.delenv("MAX_APPROVED_IMAGE_BYTES", raising=False)

    assert load_settings().max_approved_image_bytes == 5_242_880


def test_publish_image_limit_accepts_positive_environment_value(monkeypatch):
    monkeypatch.setenv("MAX_APPROVED_IMAGE_BYTES", "1024")

    assert load_settings().max_approved_image_bytes == 1024


def test_publish_image_limit_rejects_zero(monkeypatch):
    monkeypatch.setenv("MAX_APPROVED_IMAGE_BYTES", "0")

    with pytest.raises(ValueError, match="MAX_APPROVED_IMAGE_BYTES"):
        load_settings()
