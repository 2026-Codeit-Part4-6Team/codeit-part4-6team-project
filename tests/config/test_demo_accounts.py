import pytest

from backend.config import load_settings


def test_demo_accounts_are_disabled_by_default(monkeypatch):
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.delenv("DEMO_ACCOUNTS_ENABLED", raising=False)

    assert load_settings().demo_accounts_enabled is False


def test_demo_accounts_can_be_enabled_in_demo_environment(monkeypatch):
    monkeypatch.setenv("APP_ENV", "demo")
    monkeypatch.setenv("DEMO_ACCOUNTS_ENABLED", "true")

    assert load_settings().demo_accounts_enabled is True


def test_production_rejects_demo_accounts(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("DEMO_ACCOUNTS_ENABLED", "true")
    monkeypatch.setenv("SESSION_SECRET_KEY", "production-test-secret")
    monkeypatch.setenv("SESSION_COOKIE_SECURE", "true")

    with pytest.raises(ValueError, match="demo account"):
        load_settings()
