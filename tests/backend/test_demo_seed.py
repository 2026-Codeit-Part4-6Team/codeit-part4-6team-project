import asyncio
from datetime import UTC, datetime

import pytest
from pydantic import SecretStr
from sqlalchemy.orm import Session

from backend.clients.geocoding_client import GeocodingResult
from backend.database import create_database_engine
from backend.demo_seed import seed_demo_user
from backend.models import Base
from backend.schemas import RegisterRequest
from backend.services.auth_service import GeocodingPolicy

NOW = datetime(2026, 8, 14, 6, 0, tzinfo=UTC)


class StaticGeocoder:
    async def geocode(self, address: str) -> GeocodingResult:
        return GeocodingResult(road_address=address.strip(), lat=37.4979, lng=127.0276)


@pytest.fixture
def db(tmp_path):
    engine = create_database_engine(f"sqlite:///{tmp_path / 'demo-seed.db'}")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    engine.dispose()


def register_request(**overrides) -> RegisterRequest:
    values = {
        "username": "developer",
        "password": "safe-password",
        "name": "개발자",
        "email": "developer@example.com",
        "business_name": "데모 카페",
        "business_type": "카페",
        "address": "서울 강남구 테헤란로 1",
        "address_detail": None,
    }
    values.update(overrides)
    return RegisterRequest(**values)


def test_seed_rejects_production_without_querying_database(db):
    with pytest.raises(RuntimeError, match="production"):
        asyncio.run(
            seed_demo_user(
                db,
                register_request(),
                StaticGeocoder(),
                GeocodingPolicy(),
                app_env="production",
                now=NOW,
                daily_free_limit=10,
            )
        )


def test_seed_creates_demo_user_with_registration_contract(db):
    user, created = asyncio.run(
        seed_demo_user(
            db,
            register_request(),
            StaticGeocoder(),
            GeocodingPolicy(),
            app_env="demo",
            now=NOW,
            daily_free_limit=10,
        )
    )

    assert created is True
    assert user.username == "developer"
    assert user.business_name == "데모 카페"
    assert user.road_address == "서울 강남구 테헤란로 1"
    assert user.is_admin is True


def test_seed_keeps_existing_user_and_password_unchanged(db):
    first, _ = asyncio.run(
        seed_demo_user(
            db,
            register_request(),
            StaticGeocoder(),
            GeocodingPolicy(),
            app_env="demo",
            now=NOW,
            daily_free_limit=10,
        )
    )
    original_hash = first.password_hash

    second, created = asyncio.run(
        seed_demo_user(
            db,
            register_request(password=SecretStr("different-password")),
            StaticGeocoder(),
            GeocodingPolicy(),
            app_env="demo",
            now=NOW,
            daily_free_limit=10,
        )
    )

    assert created is False
    assert second.id == first.id
    assert second.password_hash == original_hash
    assert second.is_admin is True
