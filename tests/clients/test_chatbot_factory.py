import importlib
from types import SimpleNamespace

import pytest

from backend.clients import chatbot_client


def _settings(mode: str):
    return SimpleNamespace(
        chatbot_mode=mode,
        model_request_timeout_seconds=180,
        model_thread_pool_workers=2,
    )


def test_factory_keeps_actual_models_out_of_mock_mode(monkeypatch):
    def fail_import(_name):
        raise AssertionError("mock mode must not import actual model modules")

    monkeypatch.setattr(importlib, "import_module", fail_import)

    client = chatbot_client.create_chatbot_client(_settings("mock"))

    assert isinstance(client, chatbot_client.MockChatbotClient)


def test_factory_loads_both_actual_entrypoints(monkeypatch):
    def basic_run(_payload):
        return {"status": "error", "reason": "unknown", "message": "basic"}

    def consultant_run(_payload):
        return {"status": "error", "reason": "unknown", "message": "consultant"}

    modules = {
        "models.basic.main": SimpleNamespace(run=basic_run),
        "models.consult.main": SimpleNamespace(run=consultant_run),
    }
    monkeypatch.setattr(importlib, "import_module", lambda name: modules[name])

    client = chatbot_client.create_chatbot_client(_settings("actual"))

    try:
        assert isinstance(client, chatbot_client.ActualChatbotClient)
        assert client._basic is basic_run
        assert client._consultant is consultant_run
        assert client._timeout_seconds == 180
        assert client._executor._max_workers == 2
    finally:
        client.close()


def test_factory_rejects_unknown_mode():
    with pytest.raises(ValueError, match="chatbot_mode"):
        chatbot_client.create_chatbot_client(_settings("hybrid"))
