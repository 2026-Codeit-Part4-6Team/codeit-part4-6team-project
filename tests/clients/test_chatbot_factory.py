import importlib
from types import SimpleNamespace

import pytest

from backend.clients import chatbot_client


def _settings(mode: str):
    return SimpleNamespace(
        chatbot_mode=mode,
        model_request_timeout_seconds=60,
        model_thread_pool_workers=2,
    )


def test_factory_returns_mock_without_importing_actual_models(monkeypatch):
    def fail_import(_name):
        raise AssertionError("mock mode must not import actual model modules")

    monkeypatch.setattr(importlib, "import_module", fail_import)

    client = chatbot_client.create_chatbot_client(_settings("mock"))

    assert isinstance(client, chatbot_client.MockChatbotClient)


def test_factory_loads_both_actual_run_entrypoints(monkeypatch):
    def basic_run(_payload):
        return {"status": "error", "reason": "unknown", "message": "basic"}

    def consultant_run(_payload):
        return {"status": "error", "reason": "unknown", "message": "consultant"}

    modules = {
        "models.basic.main": SimpleNamespace(run=basic_run),
        "models.consult.main": SimpleNamespace(run=consultant_run),
    }
    seen = []

    def fake_import(name):
        seen.append(name)
        return modules[name]

    monkeypatch.setattr(importlib, "import_module", fake_import)

    client = chatbot_client.create_chatbot_client(_settings("actual"))

    assert isinstance(client, chatbot_client.ActualChatbotClient)
    assert client._basic is basic_run
    assert client._consultant is consultant_run
    assert client._timeout_seconds == 60
    assert client._executor._max_workers == 2
    assert seen == ["models.basic.main", "models.consult.main"]


@pytest.mark.parametrize(
    "module_name",
    ["models.basic.main", "models.consult.main"],
)
def test_factory_fails_startup_when_actual_run_is_missing(monkeypatch, module_name):
    def valid_run(_payload):
        return {"status": "error", "reason": "unknown", "message": "unused"}

    modules = {
        "models.basic.main": SimpleNamespace(run=valid_run),
        "models.consult.main": SimpleNamespace(run=valid_run),
    }
    modules[module_name] = SimpleNamespace()

    monkeypatch.setattr(importlib, "import_module", lambda name: modules[name])

    with pytest.raises(RuntimeError, match=module_name):
        chatbot_client.create_chatbot_client(_settings("actual"))


def test_factory_rejects_unknown_mode():
    with pytest.raises(ValueError, match="chatbot_mode"):
        chatbot_client.create_chatbot_client(_settings("hybrid"))
