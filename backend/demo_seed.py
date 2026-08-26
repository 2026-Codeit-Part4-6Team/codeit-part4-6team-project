"""명시적으로 실행하는 시연용 사용자 seed 명령입니다."""

import asyncio
import os
from collections.abc import Mapping
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.clients.geocoding_client import GeocodingClient, get_geocoding_client
from backend.config import settings
from backend.database import SessionLocal
from backend.models import User
from backend.schemas import RegisterRequest
from backend.services.auth_service import GeocodingPolicy, register_user

DEMO_ACCOUNT_ROLES = ("pm", "basic", "consultant", "service")
_ROLE_LABELS = {
    "pm": "PM",
    "basic": "Basic",
    "consultant": "Consultant",
    "service": "Service",
}


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


async def seed_demo_accounts(
    db: Session,
    requests: Mapping[str, RegisterRequest],
    geocoder: GeocodingClient,
    policy: GeocodingPolicy,
    *,
    app_env: str,
    now: datetime,
    daily_free_limit: int,
) -> list[tuple[str, User, bool]]:
    """역할별 데모 계정을 순서대로 만들고 기존 계정은 그대로 재사용합니다."""
    if app_env.strip().lower() == "production":
        raise RuntimeError("demo seed is disabled in production")

    seeded: list[tuple[str, User, bool]] = []
    for role, request in requests.items():
        user, created = await seed_demo_user(
            db,
            request,
            geocoder,
            policy,
            app_env=app_env,
            now=now,
            daily_free_limit=daily_free_limit,
        )
        seeded.append((role, user, created))
    return seeded


def _required_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ValueError(f"{name} is required")
    return value


def _optional_env(name: str) -> str | None:
    value = os.getenv(name, "").strip()
    return value or None


def _role_env(role: str, field: str, default: str | None = None) -> str | None:
    value = os.getenv(f"DEMO_{role.upper()}_{field}", "").strip()
    return value or default


def demo_account_requests_from_env() -> dict[str, RegisterRequest]:
    """공통 비밀번호와 역할별 override로 네 개의 데모 요청을 구성합니다."""
    shared_password = os.getenv("DEMO_ACCOUNT_PASSWORD", "").strip()
    requests: dict[str, RegisterRequest] = {}
    for role in DEMO_ACCOUNT_ROLES:
        password = _role_env(role, "PASSWORD", shared_password)
        if not password:
            raise ValueError(
                f"DEMO_ACCOUNT_PASSWORD 또는 DEMO_{role.upper()}_PASSWORD가 필요합니다"
            )
        username = _role_env(role, "USERNAME", f"demo-{role}")
        label = _ROLE_LABELS[role]
        requests[role] = RegisterRequest(
            username=username,
            password=password,
            name=_role_env(role, "NAME", f"{label} 데모 사용자"),
            email=_role_env(role, "EMAIL", f"demo-{role}@example.com"),
            business_name=_role_env(role, "BUSINESS_NAME", f"매출부스터 {label} 데모 매장"),
            business_type=_role_env(role, "BUSINESS_TYPE", "카페"),
            address=_role_env(role, "ADDRESS", "서울 강남구 테헤란로 1"),
            address_detail=_role_env(role, "ADDRESS_DETAIL"),
        )
    return requests


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


async def _run() -> list[tuple[str, User, bool]]:
    app_env = os.getenv("APP_ENV", "development")
    if app_env.strip().lower() == "production":
        raise RuntimeError("demo seed is disabled in production")
    if not settings.demo_accounts_enabled:
        raise RuntimeError("demo accounts are disabled")

    policy = GeocodingPolicy(
        fallback_enabled=settings.geocode_fallback_enabled,
        fallback_lat=settings.geocode_fallback_lat,
        fallback_lng=settings.geocode_fallback_lng,
    )
    with SessionLocal() as db:
        return await seed_demo_accounts(
            db,
            demo_account_requests_from_env(),
            get_geocoding_client(),
            policy,
            app_env=app_env,
            now=datetime.now(UTC),
            daily_free_limit=settings.daily_free_limit,
        )


def main() -> int:
    """환경변수로 개발자 계정을 생성하고 결과만 출력합니다."""
    try:
        seeded = asyncio.run(_run())
    except (RuntimeError, ValueError) as error:
        print(f"demo seed failed: {error}")
        return 2

    for role, _user, created in seeded:
        state = "created" if created else "already exists"
        # SessionLocal이 종료된 뒤 ORM 객체의 lazy/expired 필드에 접근하지 않습니다.
        # 역할명만 출력해 seed 결과를 확인하고 사용자 정보는 로그에 남기지 않습니다.
        print(f"demo user {state}: {role}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
