from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from backend.clients.geocoding_client import get_geocoding_client
from backend.database import create_database_engine, get_db
from backend.init_db import create_tables
from backend.main import create_app
from backend.models import User
from tests.fakes import SuccessfulGeocodingClient


@pytest.fixture
def session_client(tmp_path):
    """Session 인증 API와 격리 DB를 제공합니다."""
    engine = create_database_engine(f"sqlite:///{tmp_path / 'session.db'}")
    create_tables(engine)
    testing_session = sessionmaker(bind=engine, expire_on_commit=False)

    def override_get_db():
        with testing_session() as session:
            yield session

    app = create_app()
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_geocoding_client] = SuccessfulGeocodingClient
    with TestClient(app) as client:
        client.post(
            "/auth/register",
            json={
                "username": "owner",
                "password": "safe-password",
                "business_name": "카페 코드잇",
                "business_type": "카페",
                "address": "서울 강남구",
            },
        )
        yield client


def test_login_sets_secure_session_attributes_and_me_works(session_client):
    """로그인 Cookie로 현재 사용자 정보를 조회합니다."""
    response = session_client.post(
        "/auth/login", json={"username": "owner", "password": "safe-password"}
    )

    assert response.status_code == 200
    set_cookie = response.headers["set-cookie"].lower()
    assert "httponly" in set_cookie
    assert "samesite=lax" in set_cookie
    me_response = session_client.get("/users/me")
    assert me_response.status_code == 200
    assert me_response.json()["username"] == "owner"
    assert response.json()["daily_free_remaining"] == 10
    assert me_response.json()["daily_free_reset_at"] is not None
    assert me_response.json()["daily_free_remaining"] == 10


def test_login_failures_use_same_401_response(session_client):
    """계정 존재 여부와 관계없이 로그인 실패 응답은 같습니다."""
    wrong_password = session_client.post(
        "/auth/login", json={"username": "owner", "password": "wrong-password"}
    )
    unknown_user = session_client.post(
        "/auth/login", json={"username": "unknown", "password": "wrong-password"}
    )

    assert wrong_password.status_code == 401
    assert unknown_user.status_code == 401
    assert wrong_password.json() == unknown_user.json()


def test_logout_clears_session(session_client):
    """로그아웃하면 현재 사용자 조회가 다시 401을 반환합니다."""
    session_client.post(
        "/auth/login", json={"username": "owner", "password": "safe-password"}
    )
    assert session_client.get("/users/me").status_code == 200

    logout_response = session_client.post("/auth/logout")

    assert logout_response.status_code == 204
    assert session_client.get("/users/me").status_code == 401


def test_login_and_me_use_same_virtual_daily_free_snapshot(tmp_path):
    """지난 reset 상태의 사용자는 login과 /users/me에서 같은 가상 reset 값을 봅니다."""
    engine = create_database_engine(f"sqlite:///{tmp_path / 'stale-session.db'}")
    create_tables(engine)
    testing_session = sessionmaker(bind=engine, expire_on_commit=False)

    def override_get_db():
        with testing_session() as session:
            yield session

    app = create_app()
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_geocoding_client] = SuccessfulGeocodingClient
    with TestClient(app) as client:
        assert client.post(
            "/auth/register",
            json={
                "username": "stale-owner",
                "password": "safe-password",
                "business_name": "카페 코드잇",
                "business_type": "카페",
                "address": "서울 강남구",
            },
        ).status_code == 201

        stale_reset = datetime(2020, 1, 1, 0, 0)  # noqa: DTZ001
        with testing_session() as session:
            user = session.scalar(select(User).where(User.username == "stale-owner"))
            assert user is not None
            user.daily_free_used = 7
            user.daily_free_reset_at = stale_reset
            session.commit()

        login_response = client.post(
            "/auth/login",
            json={"username": "stale-owner", "password": "safe-password"},
        )
        me_response = client.get("/users/me")

        assert login_response.status_code == 200
        assert me_response.status_code == 200
        assert login_response.json()["daily_free_used"] == 0
        assert login_response.json()["daily_free_remaining"] == 10
        assert me_response.json()["daily_free_used"] == 0
        assert me_response.json()["daily_free_remaining"] == 10
        assert login_response.json()["daily_free_reset_at"] == me_response.json()[
            "daily_free_reset_at"
        ]

        with testing_session() as session:
            user = session.scalar(select(User).where(User.username == "stale-owner"))
            assert user is not None
            assert user.daily_free_used == 7
            assert user.daily_free_reset_at == stale_reset
