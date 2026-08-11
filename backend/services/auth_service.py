import logging
from dataclasses import dataclass
from datetime import UTC, datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.auth import hash_password, verify_password
from backend.clients.geocoding_client import (
    GeocodingClient,
    GeocodingProviderError,
    GeocodingResult,
)
from backend.models import User
from backend.schemas import RegisterRequest

logger = logging.getLogger(__name__)
SEOUL_TIMEZONE = ZoneInfo("Asia/Seoul")


@dataclass(frozen=True)
class GeocodingPolicy:
    """회원가입 시 지오코딩 장애 fallback 정책입니다."""

    fallback_enabled: bool = False
    fallback_lat: float = 37.4979
    fallback_lng: float = 127.0276


class DuplicateUsernameError(Exception):
    """이미 사용 중인 사용자명 오류."""


class DuplicateEmailError(Exception):
    """이미 사용 중인 이메일 오류."""


def next_daily_free_reset_at(now: datetime | None = None) -> datetime:
    """다음 한국 시각 자정을 UTC 시각으로 반환합니다."""
    current = now or datetime.now(UTC)
    local_date = current.astimezone(SEOUL_TIMEZONE).date() + timedelta(days=1)
    local_midnight = datetime.combine(local_date, time.min, tzinfo=SEOUL_TIMEZONE)
    return local_midnight.astimezone(UTC)


async def register_user(
    db: Session,
    request: RegisterRequest,
    geocoder: GeocodingClient,
    policy: GeocodingPolicy,
) -> User:
    """중복을 확인하고 사용자를 생성합니다."""
    if db.scalar(select(User.id).where(User.username == request.username)) is not None:
        raise DuplicateUsernameError
    if request.email is not None:
        email = str(request.email).lower()
        if db.scalar(select(User.id).where(User.email == email)) is not None:
            raise DuplicateEmailError
    else:
        email = None

    try:
        geocoded = await geocoder.geocode(request.address)
    except GeocodingProviderError:
        if not policy.fallback_enabled:
            raise
        logger.warning("Geocoding provider failed; registration fallback coordinates are used")
        geocoded = GeocodingResult(
            road_address=request.address,
            lat=policy.fallback_lat,
            lng=policy.fallback_lng,
        )

    user = User(
        username=request.username,
        email=email,
        password_hash=hash_password(request.password.get_secret_value()),
        name=request.name,
        business_name=request.business_name,
        business_type=request.business_type,
        address=request.address,
        address_detail=request.address_detail,
        road_address=geocoded.road_address,
        lat=geocoded.lat,
        lng=geocoded.lng,
        daily_free_reset_at=next_daily_free_reset_at(),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, username: str, password: str) -> User | None:
    """사용자명과 비밀번호가 일치하는 사용자를 반환합니다."""
    normalized = username.strip().lower()
    user = db.scalar(select(User).where(User.username == normalized))
    if user is None or not verify_password(password, user.password_hash):
        return None
    return user
