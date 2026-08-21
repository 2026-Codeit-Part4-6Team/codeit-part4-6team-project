import pytest

from backend.config import load_settings


def test_demo_test_tools_default_to_disabled(monkeypatch):
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.delenv("DEMO_TEST_TOOLS_ENABLED", raising=False)

    assert load_settings().demo_test_tools_enabled is False


def test_demo_environment_can_enable_test_tools(monkeypatch):
    monkeypatch.setenv("APP_ENV", "demo")
    monkeypatch.setenv("DEMO_TEST_TOOLS_ENABLED", "true")

    assert load_settings().demo_test_tools_enabled is True


def test_production_rejects_demo_test_tools(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("SESSION_SECRET_KEY", "production-only-secret")
    monkeypatch.setenv("SESSION_COOKIE_SECURE", "true")
    monkeypatch.setenv("DEMO_TEST_TOOLS_ENABLED", "true")

    with pytest.raises(ValueError, match="테스트 계정 도구"):
        load_settings()
