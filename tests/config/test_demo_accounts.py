import pytest

from backend.config import load_settings


def test_demo_accounts_are_disabled_by_default(monkeypatch):
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.delenv("DEMO_ACCOUNTS_ENABLED", raising=False)

    assert load_settings().demo_accounts_enabled is False


def test_demo_accounts_can_be_enabled_in_demo_environment(monkeypatch):
    monkeypatch.setenv("APP_ENV", "demo")
    monkeypatch.setenv("DEMO_ACCOUNTS_ENABLED", "true")
    monkeypatch.setenv("DEMO_ACCOUNT_PASSWORD", "shared-demo-password")

    assert load_settings().demo_accounts_enabled is True


def test_enabled_demo_accounts_require_a_password(monkeypatch):
    monkeypatch.setenv("APP_ENV", "demo")
    monkeypatch.setenv("DEMO_ACCOUNTS_ENABLED", "true")
    monkeypatch.delenv("DEMO_ACCOUNT_PASSWORD", raising=False)
    for role in ("PM", "BASIC", "CONSULTANT", "SERVICE"):
        monkeypatch.delenv(f"DEMO_{role}_PASSWORD", raising=False)

    with pytest.raises(ValueError, match="DEMO_.*PASSWORD"):
        load_settings()


def test_shared_demo_password_satisfies_each_role(monkeypatch):
    monkeypatch.setenv("APP_ENV", "demo")
    monkeypatch.setenv("DEMO_ACCOUNTS_ENABLED", "true")
    monkeypatch.setenv("DEMO_ACCOUNT_PASSWORD", "shared-demo-password")

    assert load_settings().demo_accounts_enabled is True


def test_demo_payment_defaults_on_for_non_production_demo(monkeypatch):
    monkeypatch.setenv("APP_ENV", "demo")
    monkeypatch.delenv("DEMO_PAYMENT_ENABLED", raising=False)

    assert load_settings().demo_payment_enabled is True


def test_production_rejects_demo_payment(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("DEMO_PAYMENT_ENABLED", "true")
    monkeypatch.setenv("SESSION_SECRET_KEY", "production-test-secret")
    monkeypatch.setenv("SESSION_COOKIE_SECURE", "true")

    with pytest.raises(ValueError, match="demo payment"):
        load_settings()


def test_production_rejects_demo_accounts(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("DEMO_ACCOUNTS_ENABLED", "true")
    monkeypatch.setenv("SESSION_SECRET_KEY", "production-test-secret")
    monkeypatch.setenv("SESSION_COOKIE_SECURE", "true")

    with pytest.raises(ValueError, match="demo account"):
        load_settings()
