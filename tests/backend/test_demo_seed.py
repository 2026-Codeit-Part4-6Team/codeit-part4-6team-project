import asyncio
from datetime import UTC, datetime

import pytest
from pydantic import SecretStr
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend import demo_seed
from backend.clients.geocoding_client import GeocodingResult
from backend.database import create_database_engine
from backend.demo_seed import seed_demo_user
from backend.models import Base, User
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


def test_seed_assigns_initial_credits_for_e2e_demo(db):
    user, created = asyncio.run(
        seed_demo_user(
            db,
            register_request(),
            StaticGeocoder(),
            GeocodingPolicy(),
            app_env="demo",
            now=NOW,
            daily_free_limit=10,
            initial_credits=20_000,
        )
    )

    assert created is True
    assert user.credits == 20_000
    assert user.daily_free_used == 0


def test_reset_demo_accounts_removes_only_named_users(db):
    requests = {
        role: register_request(
            username=f"demo-{role}",
            email=f"demo-{role}@example.com",
        )
        for role in ("pm", "basic", "consultant", "service")
    }
    asyncio.run(
        demo_seed.seed_demo_accounts(
            db,
            requests,
            StaticGeocoder(),
            GeocodingPolicy(),
            app_env="demo",
            now=NOW,
            daily_free_limit=10,
            initial_credits=20_000,
        )
    )
    asyncio.run(
        seed_demo_user(
            db,
            register_request(username="keep-me", email="keep@example.com"),
            StaticGeocoder(),
            GeocodingPolicy(),
            app_env="demo",
            now=NOW,
            daily_free_limit=10,
        )
    )

    # The reset helper is intentionally scoped to the four demo usernames.
    removed = demo_seed.reset_demo_accounts(
        db, tuple(request.username for request in requests.values())
    )

    assert removed == 4
    assert db.scalars(select(User)).all()[0].username == "keep-me"


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


def test_demo_account_requests_use_role_usernames_and_shared_secret(monkeypatch):
    monkeypatch.setenv("DEMO_ACCOUNT_PASSWORD", "shared-demo-password")

    requests = demo_seed.demo_account_requests_from_env()

    assert tuple(requests) == ("pm", "basic", "consultant", "service")
    assert tuple(requests[role].username for role in requests) == (
        "demo-pm",
        "demo-basic",
        "demo-consultant",
        "demo-service",
    )
    assert all(
        request.business_name == "코드잇 카페" for request in requests.values()
    )
    assert all(
        request.password.get_secret_value() == "shared-demo-password"
        for request in requests.values()
    )


def test_seed_demo_accounts_is_idempotent_for_each_role(db):
    requests = {
            role: register_request(
            username=f"demo-{role}",
            email=f"demo-{role}@example.com",
        )
        for role in ("pm", "basic", "consultant", "service")
    }

    seed = demo_seed.seed_demo_accounts
    first = asyncio.run(
        seed(
            db,
            requests,
            StaticGeocoder(),
            GeocodingPolicy(),
            app_env="demo",
            now=NOW,
            daily_free_limit=10,
        )
    )
    second = asyncio.run(
        seed(
            db,
            requests,
            StaticGeocoder(),
            GeocodingPolicy(),
            app_env="demo",
            now=NOW,
            daily_free_limit=10,
        )
    )

    assert [role for role, _user, created in first] == ["pm", "basic", "consultant", "service"]
    assert all(created for _role, _user, created in first)
    assert all(not created for _role, _user, created in second)
