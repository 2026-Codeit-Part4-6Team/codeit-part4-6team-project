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
def store_client(tmp_path) -> Generator[TestClient, None, None]:
    engine = create_database_engine(f"sqlite:///{tmp_path / 'store.db'}")
    create_tables(engine)
    testing_session = sessionmaker(bind=engine, expire_on_commit=False)

    def override_get_db():
        with testing_session() as session:
            yield session

    app = create_app()
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_geocoding_client] = SuccessfulGeocodingClient
    with TestClient(app) as client:
        response = client.post(
            "/auth/register",
            json={
                "username": "store-owner",
                "password": "safe-password",
                "business_name": "원래 가게",
                "business_type": "카페",
                "address": "서울 강남구",
            },
        )
        assert response.status_code == 201
        yield client
    engine.dispose()


def test_authenticated_user_can_update_store_profile(store_client: TestClient):
    login = store_client.post(
        "/auth/login", json={"username": "store-owner", "password": "safe-password"}
    )
    assert login.status_code == 200

    response = store_client.patch(
        "/users/me/store",
        json={
            "business_name": "바뀐 가게",
            "business_type": "베이커리",
            "address_detail": "2층",
        },
    )

    assert response.status_code == 200
    assert response.json()["business_name"] == "바뀐 가게"
    assert response.json()["business_type"] == "베이커리"
    assert response.json()["address_detail"] == "2층"
    assert store_client.get("/users/me").json()["business_name"] == "바뀐 가게"


@pytest.mark.parametrize(
    "payload",
    [
        {"business_name": "   ", "business_type": "카페"},
        {"business_name": "가게", "business_type": "\t\n"},
    ],
)
def test_store_profile_update_rejects_blank_required_fields(
    store_client: TestClient, payload: dict[str, str]
):
    login = store_client.post(
        "/auth/login", json={"username": "store-owner", "password": "safe-password"}
    )
    assert login.status_code == 200

    response = store_client.patch("/users/me/store", json=payload)

    assert response.status_code == 422
    current = store_client.get("/users/me").json()
    assert current["business_name"] == "원래 가게"
    assert current["business_type"] == "카페"


def test_store_profile_update_requires_authentication(store_client: TestClient):
    store_client.post("/auth/logout")
    response = store_client.patch(
        "/users/me/store",
        json={"business_name": "가게", "business_type": "카페", "address_detail": None},
    )

    assert response.status_code == 401
