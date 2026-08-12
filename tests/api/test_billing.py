from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from backend.auth import hash_password
from backend.clients.geocoding_client import get_geocoding_client
from backend.database import create_database_engine, get_db
from backend.init_db import create_tables
from backend.main import create_app
from backend.models import User
from tests.fakes import SuccessfulGeocodingClient


@pytest.fixture
def billing_context(tmp_path):
    """Billing estimate API와 격리 DB를 제공합니다."""
    engine = create_database_engine(f"sqlite:///{tmp_path / 'billing.db'}")
    create_tables(engine)
    testing_session = sessionmaker(bind=engine, expire_on_commit=False)

    def override_get_db():
        with testing_session() as session:
            yield session

    app = create_app()
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_geocoding_client] = SuccessfulGeocodingClient
    with testing_session() as session:
        session.add(
            User(
                username="owner",
                password_hash=hash_password("safe-password"),
                business_name="카페",
                business_type="카페",
                address="서울",
                road_address="서울",
                lat=37.5,
                lng=127.0,
                daily_free_used=0,
                daily_free_reset_at=datetime(2026, 8, 12, 15, 0, tzinfo=UTC),
            )
        )
        session.commit()
    yield app, testing_session


def login(client: TestClient) -> None:
    """테스트 사용자를 Session에 로그인시킵니다."""
    response = client.post(
        "/auth/login", json={"username": "owner", "password": "safe-password"}
    )
    assert response.status_code == 200


def test_estimate_requires_authentication(billing_context):
    """Estimate API는 Session 인증이 필요합니다."""
    app, _ = billing_context
    with TestClient(app) as client:
        response = client.post(
            "/generate/estimate",
            json={"chatbot_type": "basic", "question": "신메뉴", "platform": "instagram"},
        )

    assert response.status_code == 401


def test_estimate_does_not_mutate_user_state(billing_context):
    """Estimate API는 무료 상태와 잔액을 변경하지 않습니다."""
    app, testing_session = billing_context
    with TestClient(app) as client:
        login(client)
        before = client.get("/users/me").json()
        response = client.post(
            "/generate/estimate",
            json={"chatbot_type": "basic", "question": "신메뉴", "platform": "instagram"},
        )
        after = client.get("/users/me").json()

    assert response.status_code == 200
    assert response.json()["is_free"] is True
    assert after["daily_free_used"] == before["daily_free_used"]
    assert after["credits"] == before["credits"]
    with testing_session() as session:
        user = session.scalar(select(User).where(User.username == "owner"))
        assert user.daily_free_used == 0


def test_paid_estimate_returns_only_required_and_current_on_402(billing_context):
    """유료 잔액 부족 응답은 계약된 두 값만 노출합니다."""
    app, testing_session = billing_context
    with testing_session() as session:
        user = session.scalar(select(User).where(User.username == "owner"))
        user.daily_free_used = 10
        user.credits = 49
        session.commit()

    with TestClient(app) as client:
        login(client)
        response = client.post(
            "/generate/estimate",
            json={"chatbot_type": "consultant", "question": "전략", "platform": None},
        )

    assert response.status_code == 402
    assert response.json()["detail"] == {"required": 50, "current": 49}
