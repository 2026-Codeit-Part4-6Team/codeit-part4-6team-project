from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from backend.clients.geocoding_client import get_geocoding_client
from backend.database import create_database_engine, get_db
from backend.init_db import create_tables
from backend.main import create_app
from tests.fakes import SuccessfulGeocodingClient


@pytest.fixture
def payment_client(tmp_path) -> Generator[TestClient, None, None]:
    engine = create_database_engine(f"sqlite:///{tmp_path / 'payments.db'}")
    create_tables(engine)
    testing_session = sessionmaker(bind=engine, expire_on_commit=False)

    def override_get_db():
        with testing_session() as session:
            yield session

    app = create_app()
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_geocoding_client] = SuccessfulGeocodingClient
    with TestClient(app) as client:
        registered = client.post(
            "/auth/register",
            json={
                "username": "payment-owner",
                "password": "safe-password",
                "business_name": "결제 가게",
                "business_type": "카페",
                "address": "서울 강남구",
            },
        )
        assert registered.status_code == 201
        logged_in = client.post(
            "/auth/login", json={"username": "payment-owner", "password": "safe-password"}
        )
        assert logged_in.status_code == 200
        yield client
    engine.dispose()


def test_catalog_exposes_confirmed_policy_prices(payment_client: TestClient):
    response = payment_client.get("/payments/catalog")

    assert response.status_code == 200
    assert response.json() == {
        "currency": "KRW",
        "vat_included": False,
        "unit_price": 10,
        "packages": [
            {"id": "starter", "credits": 5_000, "amount": 48_500, "discount_percent": 3},
            {"id": "standard", "credits": 10_000, "amount": 93_000, "discount_percent": 7},
            {"id": "pro", "credits": 20_000, "amount": 180_000, "discount_percent": 10},
        ],
    }


def test_purchase_increases_credits_and_is_idempotent(payment_client: TestClient):
    key = "00000000-0000-0000-0000-000000000901"
    first = payment_client.post(
        "/payments", json={"package": "starter"}, headers={"Idempotency-Key": key}
    )
    replay = payment_client.post(
        "/payments", json={"package": "starter"}, headers={"Idempotency-Key": key}
    )

    assert first.status_code == 201
    assert first.json()["credits"] == 5_000
    assert first.json()["amount"] == 48_500
    assert first.json()["vat_included"] is False
    assert first.json()["provider"] == "pending"
    assert replay.status_code == 201
    assert replay.json() == first.json()
    assert payment_client.get("/users/me").json()["credits"] == 5_000


def test_reusing_key_for_another_package_is_rejected(payment_client: TestClient):
    key = "00000000-0000-0000-0000-000000000902"
    assert payment_client.post(
        "/payments", json={"package": "starter"}, headers={"Idempotency-Key": key}
    ).status_code == 201

    response = payment_client.post(
        "/payments", json={"package": "pro"}, headers={"Idempotency-Key": key}
    )

    assert response.status_code == 409
    assert response.json()["detail"]["reason"] == "payment_idempotency_conflict"
