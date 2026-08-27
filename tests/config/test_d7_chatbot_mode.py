import pytest

from backend.config import load_settings


def test_chatbot_mode_defaults_to_mock(monkeypatch):
    monkeypatch.delenv("CHATBOT_MODE", raising=False)

    assert load_settings().chatbot_mode == "mock"


def test_chatbot_mode_accepts_actual(monkeypatch):
    monkeypatch.setenv("CHATBOT_MODE", "actual")

    assert load_settings().chatbot_mode == "actual"


def test_chatbot_mode_rejects_unknown_value(monkeypatch):
    monkeypatch.setenv("CHATBOT_MODE", "hybrid")

    with pytest.raises(ValueError, match="CHATBOT_MODE"):
        load_settings()
