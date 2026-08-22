from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.auth import get_current_user
from backend.config import settings
from backend.models import Payment, User


def add_user(db: Session) -> User:
    user = User(username="demo-payer", password_hash="unused", credits=100)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def set_demo_payment_enabled(enabled: bool):
    previous = getattr(settings, "demo_payment_enabled", None)
    object.__setattr__(settings, "demo_payment_enabled", enabled)
    return previous


def restore_demo_payment_enabled(previous):
    if previous is None:
        object.__delattr__(settings, "demo_payment_enabled")
    else:
        object.__setattr__(settings, "demo_payment_enabled", previous)


def test_demo_catalog_is_available_only_when_enabled(client: TestClient):
    previous = set_demo_payment_enabled(True)
    try:
        response = client.get("/payments/catalog")
    finally:
        restore_demo_payment_enabled(previous)

    assert response.status_code == 200
    assert response.json() == {
        "demo_enabled": True,
        "packages": [
            {"id": "starter", "amount": 48500, "credits": 5000, "discount_percent": 3},
            {"id": "standard", "amount": 93000, "credits": 10000, "discount_percent": 7},
            {"id": "pro", "amount": 180000, "credits": 20000, "discount_percent": 10},
        ],
    }


def test_demo_payment_is_idempotent_and_updates_credit_once(
    client: TestClient, db_session: Session
):
    owner = add_user(db_session)
    client.app.dependency_overrides[get_current_user] = lambda: owner
    previous = set_demo_payment_enabled(True)
    key = "00000000-0000-0000-0000-000000000901"
    try:
        first = client.post(
            "/payments",
            headers={"Idempotency-Key": key},
            json={"package": "starter"},
        )
        second = client.post(
            "/payments",
            headers={"Idempotency-Key": key},
            json={"package": "starter"},
        )
    finally:
        restore_demo_payment_enabled(previous)

    assert first.status_code == 201
    assert second.status_code == 201
    assert second.json() == first.json()
    assert first.json() == {
        "payment_id": first.json()["payment_id"],
        "package": "starter",
        "amount": 48500,
        "credits": 5000,
        "discount_percent": 3,
        "balance": 5100,
        "status": "completed",
        "demo": True,
    }
    db_session.refresh(owner)
    assert owner.credits == 5100
    assert db_session.query(Payment).filter_by(user_id=owner.id).count() == 1
    assert db_session.query(Payment).one().idempotency_key == key


def test_demo_payment_disabled_does_not_mutate_credit(
    client: TestClient, db_session: Session
):
    owner = add_user(db_session)
    client.app.dependency_overrides[get_current_user] = lambda: owner
    previous = set_demo_payment_enabled(False)
    try:
        response = client.post(
            "/payments",
            headers={"Idempotency-Key": "00000000-0000-0000-0000-000000000902"},
            json={"package": "starter"},
        )
    finally:
        restore_demo_payment_enabled(previous)

    assert response.status_code == 404
    db_session.refresh(owner)
    assert owner.credits == 100
    assert db_session.query(Payment).count() == 0
