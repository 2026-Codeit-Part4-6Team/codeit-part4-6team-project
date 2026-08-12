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
def registration_context(tmp_path):
    """회원가입 API와 격리 DB를 제공합니다."""
    engine = create_database_engine(f"sqlite:///{tmp_path / 'auth.db'}")
    create_tables(engine)
    testing_session = sessionmaker(bind=engine, expire_on_commit=False)

    def override_get_db():
        with testing_session() as session:
            yield session

    app = create_app()
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_geocoding_client] = SuccessfulGeocodingClient
    with TestClient(app) as client:
        yield client, testing_session


def valid_registration(**overrides):
    """유효한 회원가입 요청을 생성합니다."""
    payload = {
        "username": "codeit_owner",
        "password": "safe-password",
        "name": "홍길동",
        "email": "owner@example.com",
        "business_name": "카페 코드잇",
        "business_type": "카페",
        "address": "서울특별시 강남구 역삼동",
        "address_detail": None,
    }
    payload.update(overrides)
    return payload


def test_register_stores_normalized_username_and_bcrypt_hash(registration_context):
    """회원가입은 정규화한 사용자명과 bcrypt 해시를 저장합니다."""
    client, testing_session = registration_context

    response = client.post(
        "/auth/register", json=valid_registration(username="  Codeit_Owner  ")
    )

    assert response.status_code == 201
    assert response.json()["username"] == "codeit_owner"
    assert response.json()["daily_free_reset_at"] is not None
    assert "password" not in response.json()
    with testing_session() as session:
        user = session.scalar(select(User).where(User.username == "codeit_owner"))
        assert user is not None
        assert user.password_hash != "safe-password"
        assert user.password_hash.startswith("$2")


def test_register_rejects_duplicate_username_and_email(registration_context):
    """중복 사용자명과 이메일은 구분되는 409 응답입니다."""
    client, _ = registration_context
    assert client.post("/auth/register", json=valid_registration()).status_code == 201

    username_response = client.post(
        "/auth/register",
        json=valid_registration(username="CODEIT_OWNER", email="other@example.com"),
    )
    email_response = client.post(
        "/auth/register",
        json=valid_registration(username="other", email="owner@example.com"),
    )

    assert username_response.status_code == 409
    assert username_response.json()["detail"]["code"] == "duplicate_username"
    assert email_response.status_code == 409
    assert email_response.json()["detail"]["code"] == "duplicate_email"


def test_register_validation_does_not_echo_password(registration_context):
    """입력 검증 오류는 원문 비밀번호를 노출하지 않습니다."""
    client, _ = registration_context

    response = client.post(
        "/auth/register", json=valid_registration(password="secret", business_name="")
    )

    assert response.status_code == 422
    assert "secret" not in response.text


def test_register_rejects_password_over_72_utf8_bytes(registration_context):
    """UTF-8 바이트 기준 bcrypt 제한을 넘는 비밀번호는 거부합니다."""
    client, _ = registration_context

    response = client.post(
        "/auth/register",
        json=valid_registration(password="가" * 25),
    )

    assert response.status_code == 422
