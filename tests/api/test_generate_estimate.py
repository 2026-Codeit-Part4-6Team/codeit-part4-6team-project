from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.auth import get_current_user
from backend.database import create_database_engine, get_db
from backend.init_db import create_tables
from backend.main import create_app
from backend.models import User


@pytest.fixture
def estimate_client(tmp_path):
    engine = create_database_engine(f"sqlite:///{tmp_path / 'generate-estimate-api.db'}")
    create_tables(engine)
    session = Session(engine, expire_on_commit=False)
    app = create_app()
    app.dependency_overrides[get_db] = lambda: session
    try:
        with TestClient(app) as client:
            yield client, session
    finally:
        app.dependency_overrides.clear()
        session.close()


def test_estimate_requires_authentication(estimate_client):
    client, _ = estimate_client
    response = client.post(
        "/generate/estimate",
        json={"chatbot_type": "basic", "question": "광고", "platform": "instagram"},
    )
    assert response.status_code == 401


def test_estimate_returns_402_without_mutating_credit(estimate_client):
    client, session = estimate_client
    user = User(
        username="poor-api",
        password_hash="unused",
        credits=49,
        daily_free_used=10,
        daily_free_reset_at=datetime.now(UTC) + timedelta(hours=12),
    )
    session.add(user)
    session.commit()
    client.app.dependency_overrides[get_current_user] = lambda: user
    try:
        response = client.post(
            "/generate/estimate",
            json={"chatbot_type": "basic", "question": "광고", "platform": "instagram"},
        )
    finally:
        client.app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 402
    assert response.json() == {
        "detail": {
            "code": "insufficient_credits",
            "message": "Credit이 부족합니다.",
            "required": 50,
            "current": 49,
        }
    }
    session.refresh(user)
    assert user.credits == 49
    assert user.daily_free_used == 10


def test_estimate_returns_free_snapshot_without_mutation(estimate_client):
    client, session = estimate_client
    user = User(
        username="free-api",
        password_hash="unused",
        credits=25,
        daily_free_used=3,
        daily_free_reset_at=datetime.now(UTC) + timedelta(hours=12),
    )
    session.add(user)
    session.commit()

    client.app.dependency_overrides[get_current_user] = lambda: user
    try:
        response = client.post(
            "/generate/estimate",
            json={"chatbot_type": "consultant", "question": "상권 분석"},
        )
    finally:
        client.app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 200
    assert response.json() == {
        "is_free": True,
        "free_remaining": 7,
        "estimated_credits": 0,
        "current_credits": 25,
        "credits_after": 25,
        "requires_confirmation": False,
    }
    session.refresh(user)
    assert user.daily_free_used == 3
    assert user.credits == 25


def test_estimate_schema_rejects_unknown_chatbot_type_with_422(estimate_client):
    client, session = estimate_client
    user = User(username="schema-api", password_hash="unused")
    session.add(user)
    session.commit()

    client.app.dependency_overrides[get_current_user] = lambda: user
    try:
        response = client.post(
            "/generate/estimate",
            json={"chatbot_type": "unknown", "question": "광고"},
        )
    finally:
        client.app.dependency_overrides.pop(get_current_user, None)
    assert response.status_code == 422
