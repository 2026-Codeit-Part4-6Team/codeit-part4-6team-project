import logging
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import sessionmaker

from backend.clients.geocoding_client import (
    GeocodingNotFound,
    GeocodingProviderError,
    GeocodingResult,
    get_geocoding_client,
)
from backend.config import load_settings
from backend.database import create_database_engine, get_db
from backend.init_db import create_tables
from backend.main import create_app
from backend.models import User
from backend.routers.auth_router import GeocodingPolicy, get_geocoding_policy
from backend.services.auth_service import next_daily_free_reset_at


class FakeGeocodingClient:
    """회원가입 테스트에서 지정된 결과나 오류를 반환합니다."""

    def __init__(self, result=None, error: Exception | None = None) -> None:
        self.result = result
        self.error = error

    async def geocode(self, _address: str) -> GeocodingResult:
        """설정한 결과를 반환하거나 오류를 발생시킵니다."""
        if self.error is not None:
            raise self.error
        return self.result


@pytest.fixture
def geocoding_context(tmp_path):
    """지오코딩 회원가입 API와 격리 DB를 제공합니다."""
    engine = create_database_engine(f"sqlite:///{tmp_path / 'geocoding.db'}")
    create_tables(engine)
    testing_session = sessionmaker(bind=engine, expire_on_commit=False)
    app = create_app()

    def override_get_db():
        with testing_session() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    yield app, testing_session


def registration_payload():
    """지오코딩 테스트용 회원가입 요청을 생성합니다."""
    return {
        "username": "owner",
        "password": "safe-password",
        "business_name": "카페 코드잇",
        "business_type": "카페",
        "address": "서울 강남구 테헤란로 1",
    }


def user_count(testing_session) -> int:
    """격리 DB에 저장된 사용자 수를 반환합니다."""
    with testing_session() as session:
        return session.scalar(select(func.count()).select_from(User))


def test_next_daily_reset_uses_korean_midnight():
    """무료 사용량 리셋 시각은 다음 한국 자정의 UTC 시각입니다."""
    now = datetime(2026, 8, 11, 16, 0, tzinfo=UTC)

    result = next_daily_free_reset_at(now)

    assert result == datetime(2026, 8, 12, 15, 0, tzinfo=UTC)


def test_register_saves_geocoded_address_and_next_reset_at(geocoding_context):
    """회원가입 성공 시 정규화 주소와 좌표, 다음 리셋 시각을 저장합니다."""
    app, testing_session = geocoding_context
    app.dependency_overrides[get_geocoding_client] = lambda: FakeGeocodingClient(
        GeocodingResult(
            road_address="서울특별시 강남구 테헤란로 1",
            lat=37.4979,
            lng=127.0276,
        )
    )

    with TestClient(app) as client:
        response = client.post("/auth/register", json=registration_payload())

    assert response.status_code == 201
    with testing_session() as session:
        user = session.scalar(select(User).where(User.username == "owner"))
        assert user is not None
        assert user.road_address == "서울특별시 강남구 테헤란로 1"
        assert user.lat == pytest.approx(37.4979)
        assert user.lng == pytest.approx(127.0276)
        assert user.daily_free_reset_at is not None


def test_register_returns_422_and_saves_nothing_when_address_is_not_found(
    geocoding_context,
):
    """검색 결과가 없는 주소는 사용자 입력 오류로 처리합니다."""
    app, testing_session = geocoding_context
    app.dependency_overrides[get_geocoding_client] = lambda: FakeGeocodingClient(
        error=GeocodingNotFound("주소 없음")
    )

    with TestClient(app) as client:
        response = client.post("/auth/register", json=registration_payload())

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "address_not_found"
    assert user_count(testing_session) == 0


def test_register_returns_503_and_saves_nothing_on_provider_failure(geocoding_context):
    """제공자 장애 시 fallback이 꺼져 있으면 가입을 중단합니다."""
    app, testing_session = geocoding_context
    app.dependency_overrides[get_geocoding_client] = lambda: FakeGeocodingClient(
        error=GeocodingProviderError("장애")
    )

    with TestClient(app) as client:
        response = client.post("/auth/register", json=registration_payload())

    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "geocoding_unavailable"
    assert user_count(testing_session) == 0


def test_register_uses_configured_fallback_only_for_provider_failure(
    geocoding_context, caplog
):
    """시연 fallback이 켜진 제공자 장애만 기본 좌표로 가입을 허용합니다."""
    app, testing_session = geocoding_context
    app.dependency_overrides[get_geocoding_client] = lambda: FakeGeocodingClient(
        error=GeocodingProviderError("장애")
    )
    app.dependency_overrides[get_geocoding_policy] = lambda: GeocodingPolicy(
        fallback_enabled=True,
        fallback_lat=37.4979,
        fallback_lng=127.0276,
    )

    with caplog.at_level(logging.WARNING), TestClient(app) as client:
        response = client.post("/auth/register", json=registration_payload())

    assert response.status_code == 201
    assert "fallback" in caplog.text.lower()
    with testing_session() as session:
        user = session.scalar(select(User).where(User.username == "owner"))
        assert user is not None
        assert user.road_address == registration_payload()["address"]
        assert user.lat == pytest.approx(37.4979)
        assert user.lng == pytest.approx(127.0276)


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("GEOCODE_FALLBACK_LAT", "91"),
        ("GEOCODE_FALLBACK_LNG", "181"),
        ("GEOCODE_FALLBACK_LAT", "nan"),
    ],
)
def test_settings_rejects_invalid_fallback_coordinates(monkeypatch, name, value):
    """Fallback 좌표는 유효한 위도·경도 범위의 유한값이어야 합니다."""
    monkeypatch.setenv(name, value)

    with pytest.raises(ValueError, match="좌표"):
        load_settings()


def test_production_settings_require_secret_and_secure_cookie(monkeypatch):
    """운영 설정은 기본 Secret과 비보안 Cookie를 허용하지 않습니다."""
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.delenv("SESSION_SECRET_KEY", raising=False)
    monkeypatch.setenv("SESSION_COOKIE_SECURE", "false")

    with pytest.raises(ValueError, match="SESSION_SECRET_KEY"):
        load_settings()


def test_production_settings_reject_fallback_and_unknown_environment(monkeypatch):
    """운영 환경은 fallback을 끄고 알려진 환경명만 사용합니다."""
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("SESSION_SECRET_KEY", "real-secret")
    monkeypatch.setenv("SESSION_COOKIE_SECURE", "true")
    monkeypatch.setenv("GEOCODE_FALLBACK_ENABLED", "true")

    with pytest.raises(ValueError, match="fallback"):
        load_settings()

    monkeypatch.setenv("APP_ENV", "prod")
    monkeypatch.setenv("GEOCODE_FALLBACK_ENABLED", "false")
    with pytest.raises(ValueError, match="APP_ENV"):
        load_settings()
