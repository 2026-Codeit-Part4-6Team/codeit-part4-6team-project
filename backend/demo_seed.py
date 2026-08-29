"""명시적으로 실행하는 시연용 사용자 seed 명령입니다."""

import argparse
import asyncio
import os
from collections.abc import Mapping
from datetime import UTC, datetime

from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session

from backend.clients.geocoding_client import GeocodingClient, get_geocoding_client
from backend.config import settings
from backend.database import SessionLocal
from backend.models import Generation, Payment, User
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
    initial_credits: int = 0,
    topup: bool = False,
) -> tuple[User, bool]:
    """개발·시연 환경 계정을 준비하고 필요하면 기존 잔액만 보충합니다."""
    if app_env.strip().lower() == "production":
        raise RuntimeError("demo seed is disabled in production")
    if initial_credits < 0:
        raise ValueError("initial_credits는 0 이상이어야 합니다.")

    existing = db.scalar(select(User).where(User.username == request.username))
    if existing is not None:
        if topup:
            existing.credits = initial_credits
            db.commit()
            db.refresh(existing)
        return existing, False

    user = await register_user(
        db,
        request,
        geocoder,
        policy,
        now=now,
        daily_free_limit=daily_free_limit,
    )
    user.credits = initial_credits
    db.commit()
    db.refresh(user)
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
    initial_credits: int = 0,
    topup: bool = False,
) -> list[tuple[str, User, bool]]:
    """역할별 데모 계정을 만들고 선택적으로 기존 잔액을 보충합니다."""
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
            initial_credits=initial_credits,
            topup=topup,
        )
        seeded.append((role, user, created))
    return seeded


def reset_demo_accounts(db: Session, usernames: tuple[str, ...]) -> int:
    """지정한 데모 사용자와 그 생성·결제 이력만 초기화합니다."""
    normalized = tuple(
        dict.fromkeys(username.strip().lower() for username in usernames if username.strip())
    )
    if not normalized:
        return 0

    users = list(db.scalars(select(User).where(User.username.in_(normalized))))
    if not users:
        return 0

    user_ids = [user.id for user in users]
    generation_ids = list(
        db.scalars(select(Generation.id).where(Generation.user_id.in_(user_ids)))
    )
    if generation_ids:
        # 파생 생성이 원본 생성의 self-FK를 참조할 수 있으므로 먼저 연결을 끊습니다.
        db.execute(
            update(Generation)
            .where(Generation.source_gen_id.in_(generation_ids))
            .values(source_gen_id=None)
        )
        db.execute(delete(Generation).where(Generation.id.in_(generation_ids)))
    db.execute(delete(Payment).where(Payment.user_id.in_(user_ids)))
    db.execute(delete(User).where(User.id.in_(user_ids)))
    db.commit()
    return len(users)


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
            business_name=_role_env(role, "BUSINESS_NAME", "코드잇 카페"),
            business_type=_role_env(role, "BUSINESS_TYPE", "카페"),
            address=_role_env(role, "ADDRESS", "서울 강남구 역삼동"),
            address_detail=_role_env(role, "ADDRESS_DETAIL"),
        )
    return requests


def _initial_credits_from_env() -> int:
    raw = os.getenv("DEMO_INITIAL_CREDITS", "20000").strip()
    try:
        value = int(raw)
    except ValueError as error:
        raise ValueError("DEMO_INITIAL_CREDITS는 정수여야 합니다") from error
    if value < 0:
        raise ValueError("DEMO_INITIAL_CREDITS는 0 이상이어야 합니다")
    return value


async def _run(*, reset: bool = False, topup: bool = False) -> list[tuple[str, User, bool]]:
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
        requests = demo_account_requests_from_env()
        if reset:
            reset_demo_accounts(db, tuple(request.username for request in requests.values()))
        return await seed_demo_accounts(
            db,
            requests,
            get_geocoding_client(),
            policy,
            app_env=app_env,
            now=datetime.now(UTC),
            daily_free_limit=settings.daily_free_limit,
            initial_credits=_initial_credits_from_env(),
            topup=topup,
        )


def main(argv: list[str] | None = None) -> int:
    """환경변수로 개발자 계정을 생성하고 결과만 출력합니다."""
    parser = argparse.ArgumentParser(description="로컬/시연용 역할별 계정 seed")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="지정된 데모 계정과 생성·결제 이력을 삭제한 뒤 다시 생성합니다.",
    )
    parser.add_argument(
        "--topup",
        action="store_true",
        help="기존 데모 계정의 크레딧만 DEMO_INITIAL_CREDITS로 보충하고 이력은 유지합니다.",
    )
    args = parser.parse_args(argv)
    try:
        seeded = asyncio.run(_run(reset=args.reset, topup=args.topup))
    except (RuntimeError, ValueError) as error:
        print(f"demo seed failed: {error}")
        return 2

    for role, _user, created in seeded:
        state = "created" if created else ("topped up" if args.topup else "already exists")
        # SessionLocal이 종료된 뒤 ORM 객체의 lazy/expired 필드에 접근하지 않습니다.
        # 역할명만 출력해 seed 결과를 확인하고 사용자 정보는 로그에 남기지 않습니다.
        print(f"demo user {state}: {role}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
