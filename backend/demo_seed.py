"""명시적으로 실행하는 시연용 사용자 seed 명령입니다."""

import asyncio
import os
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.clients.geocoding_client import GeocodingClient, get_geocoding_client
from backend.config import settings
from backend.database import SessionLocal
from backend.models import User
from backend.schemas import RegisterRequest
from backend.services.auth_service import GeocodingPolicy, register_user


async def seed_demo_user(
    db: Session,
    request: RegisterRequest,
    geocoder: GeocodingClient,
    policy: GeocodingPolicy,
    *,
    app_env: str,
    now: datetime,
    daily_free_limit: int,
) -> tuple[User, bool]:
    """기존 사용자를 변경하지 않고 개발·시연 환경에 계정을 준비합니다."""
    if app_env.strip().lower() == "production":
        raise RuntimeError("demo seed is disabled in production")

    existing = db.scalar(select(User).where(User.username == request.username))
    if existing is not None:
        return existing, False

    user = await register_user(
        db,
        request,
        geocoder,
        policy,
        now=now,
        daily_free_limit=daily_free_limit,
    )
    return user, True


def _required_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ValueError(f"{name} is required")
    return value


def _optional_env(name: str) -> str | None:
    value = os.getenv(name, "").strip()
    return value or None


def _request_from_env() -> RegisterRequest:
    return RegisterRequest(
        username=_required_env("DEMO_USERNAME"),
        password=_required_env("DEMO_PASSWORD"),
        name=_optional_env("DEMO_NAME"),
        email=_optional_env("DEMO_EMAIL"),
        business_name=_required_env("DEMO_BUSINESS_NAME"),
        business_type=_required_env("DEMO_BUSINESS_TYPE"),
        address=_required_env("DEMO_ADDRESS"),
        address_detail=_optional_env("DEMO_ADDRESS_DETAIL"),
    )


async def _run() -> tuple[User, bool]:
    app_env = os.getenv("APP_ENV", "development")
    if app_env.strip().lower() == "production":
        raise RuntimeError("demo seed is disabled in production")

    policy = GeocodingPolicy(
        fallback_enabled=settings.geocode_fallback_enabled,
        fallback_lat=settings.geocode_fallback_lat,
        fallback_lng=settings.geocode_fallback_lng,
    )
    with SessionLocal() as db:
        return await seed_demo_user(
            db,
            _request_from_env(),
            get_geocoding_client(),
            policy,
            app_env=app_env,
            now=datetime.now(UTC),
            daily_free_limit=settings.daily_free_limit,
        )


def main() -> int:
    """환경변수로 개발자 계정을 생성하고 결과만 출력합니다."""
    try:
        user, created = asyncio.run(_run())
    except (RuntimeError, ValueError) as error:
        print(f"demo seed failed: {error}")
        return 2

    state = "created" if created else "already exists"
    print(f"demo user {state}: {user.username}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
