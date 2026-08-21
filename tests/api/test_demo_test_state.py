from datetime import UTC, datetime

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.auth import get_current_user
from backend.config import settings
from backend.models import User


def add_user(db: Session, *, is_admin: bool) -> User:
    user = User(
        username="demo-admin" if is_admin else "ordinary-user",
        password_hash="unused",
        credits=100,
        daily_free_used=2,
        daily_free_reset_at=datetime(2026, 8, 22, 15, 0, tzinfo=UTC),
        is_admin=is_admin,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def set_demo_test_tools_enabled(enabled: bool) -> bool:
    previous = settings.demo_test_tools_enabled
    object.__setattr__(settings, "demo_test_tools_enabled", enabled)
    return previous


def restore_demo_test_tools_enabled(previous: bool) -> None:
    object.__setattr__(settings, "demo_test_tools_enabled", previous)


def test_admin_can_set_own_demo_credit_and_daily_usage(
    client: TestClient, db_session: Session
):
    owner = add_user(db_session, is_admin=True)
    client.app.dependency_overrides[get_current_user] = lambda: owner
    previous = set_demo_test_tools_enabled(True)
    try:
        response = client.post(
            "/demo/test-state",
            json={"credits": 1234, "daily_free_used": 7},
        )
    finally:
        restore_demo_test_tools_enabled(previous)

    assert response.status_code == 200
    assert response.json()["credits"] == 1234
    assert response.json()["daily_free_used"] == 7
    assert response.json()["daily_free_remaining"] == 3
    assert response.json()["is_admin"] is True
    db_session.refresh(owner)
    assert owner.credits == 1234
    assert owner.daily_free_used == 7
    assert owner.daily_free_reset_at is not None


def test_non_admin_cannot_change_demo_state(client: TestClient, db_session: Session):
    owner = add_user(db_session, is_admin=False)
    client.app.dependency_overrides[get_current_user] = lambda: owner
    previous = set_demo_test_tools_enabled(True)
    try:
        response = client.post(
            "/demo/test-state",
            json={"credits": 9999, "daily_free_used": 9},
        )
    finally:
        restore_demo_test_tools_enabled(previous)

    assert response.status_code == 403
    db_session.refresh(owner)
    assert owner.credits == 100
    assert owner.daily_free_used == 2


def test_disabled_demo_tools_hide_endpoint_without_mutation(
    client: TestClient, db_session: Session
):
    owner = add_user(db_session, is_admin=True)
    client.app.dependency_overrides[get_current_user] = lambda: owner
    previous = set_demo_test_tools_enabled(False)
    try:
        response = client.post(
            "/demo/test-state",
            json={"credits": 9999, "daily_free_used": 9},
        )
    finally:
        restore_demo_test_tools_enabled(previous)

    assert response.status_code == 404
    db_session.refresh(owner)
    assert owner.credits == 100
    assert owner.daily_free_used == 2


def test_daily_usage_cannot_exceed_configured_limit(
    client: TestClient, db_session: Session
):
    owner = add_user(db_session, is_admin=True)
    client.app.dependency_overrides[get_current_user] = lambda: owner
    previous = set_demo_test_tools_enabled(True)
    try:
        response = client.post(
            "/demo/test-state",
            json={"credits": 100, "daily_free_used": settings.daily_free_limit + 1},
        )
    finally:
        restore_demo_test_tools_enabled(previous)

    assert response.status_code == 422
    db_session.refresh(owner)
    assert owner.daily_free_used == 2
