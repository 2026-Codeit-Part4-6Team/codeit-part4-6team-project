import importlib
import sys
import types

from fastapi import APIRouter


def test_create_app_wires_one_chatbot_client_instance(monkeypatch):
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
    sys.modules.pop("backend.main", None)

    main = importlib.import_module("backend.main")
    app = main.create_app()

    assert hasattr(app.state, "chatbot_client")
    client = app.state.chatbot_client
    assert client is app.state.chatbot_client
