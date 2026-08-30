import asyncio
import importlib
import sys
import types

from fastapi import APIRouter


def test_create_app_wires_one_chatbot_client_from_factory(monkeypatch):
    fake_bcrypt = types.SimpleNamespace(
        hashpw=lambda value, _salt: value,
        gensalt=lambda: b"salt",
        checkpw=lambda _value, _hashed: True,
    )
    monkeypatch.setitem(sys.modules, "bcrypt", fake_bcrypt)
    monkeypatch.setitem(
        sys.modules,
        "backend.routers.generate_router",
        types.SimpleNamespace(router=APIRouter()),
    )

    from backend.clients import chatbot_client

    sentinel = object()
    calls = []

    def fake_factory(settings):
        calls.append(settings)
        return sentinel

    monkeypatch.setattr(chatbot_client, "create_chatbot_client", fake_factory)
    sys.modules.pop("backend.main", None)

    main = importlib.import_module("backend.main")
    calls.clear()

    app = main.create_app()

    assert calls == [main.settings]
    assert app.state.chatbot_client is sentinel
    assert app.state.chatbot_client is sentinel


def test_actual_app_lifespan_preloads_huggingface_weights(monkeypatch):
    from backend import main

    calls = []
    monkeypatch.setattr(main, "settings", type("Settings", (), {"chatbot_mode": "actual"})())
    monkeypatch.setattr(main, "preload_actual_model_weights", lambda: calls.append("preload"))

    async def exercise_lifespan():
        async with main.lifespan(object()):
            assert calls == ["preload"]

    asyncio.run(exercise_lifespan())
