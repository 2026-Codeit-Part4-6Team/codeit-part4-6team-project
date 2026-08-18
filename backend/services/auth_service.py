import hashlib
import logging
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.auth import hash_password, verify_password
from backend.clients.geocoding_client import (
    GeocodingClient,
    GeocodingNotFound,
    GeocodingProviderError,
    GeocodingResult,
)
from backend.models import User
from backend.schemas import RegisterRequest, UserResponse
from backend.services.usage_service import (
    _bind_utc,
    effective_daily_usage,
    next_seoul_midnight_utc,
)

logger = logging.getLogger(__name__)

# 존재하지 않는 사용자도 실제 계정과 같은 bcrypt 비용을 지불해 계정 열거를 막습니다.
_DUMMY_PASSWORD_HASH = "$2b$12$/52SmX1dcVwt9j2y1ihQCON4OfIi0y0mWn0yYIiUNsf4Djl04T0w6"

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
    """D2 호환 wrapper: 다음 한국 시각 자정을 UTC로 반환합니다."""
    return next_seoul_midnight_utc(now or datetime.now(UTC))


def build_user_response(
    user: User,
    *,
    now: datetime,
    daily_free_limit: int,
) -> UserResponse:
    """DB를 변경하지 않고 현재 시각 기준 무료 사용량 snapshot을 구성합니다."""
    if daily_free_limit < 0:
        raise ValueError("daily_free_limit은 0 이상이어야 합니다.")

    daily_free_used, daily_free_reset_at = effective_daily_usage(user, now)

    return UserResponse(
        id=user.id,
        username=user.username,
        name=user.name,
        email=user.email,
        business_name=user.business_name,
        business_type=user.business_type,
        address=user.address,
        address_detail=user.address_detail,
        road_address=user.road_address,
        lat=user.lat,
        lng=user.lng,
        credits=user.credits,
        daily_free_used=daily_free_used,
        daily_free_reset_at=daily_free_reset_at,
        daily_free_remaining=max(0, daily_free_limit - daily_free_used),
    )


async def register_user(
    db: Session,
    request: RegisterRequest,
    geocoder: GeocodingClient,
    policy: GeocodingPolicy,
    *,
    now: datetime,
    daily_free_limit: int,
) -> User:
    """중복을 확인하고 사용자를 생성합니다."""
    if daily_free_limit < 0:
        raise ValueError("daily_free_limit은 0 이상이어야 합니다.")
    if db.scalar(select(User.id).where(User.username == request.username)) is not None:
        raise DuplicateUsernameError
    if request.email is not None:
        email = str(request.email).lower()
        if db.scalar(select(User.id).where(User.email == email)) is not None:
            raise DuplicateEmailError
    else:
        email = None

    db.rollback()
    try:
        geocoded = await geocoder.geocode(request.address)
    except GeocodingNotFound:
        db.rollback()
        raise
    except GeocodingProviderError:
        db.rollback()
        if not policy.fallback_enabled:
            raise
        registration_id = hashlib.sha256(request.username.encode("utf-8")).hexdigest()[:12]
        logger.warning(
            "Geocoding provider failed; registration fallback coordinates are used "
            "registration_id=%s",
            registration_id,
        )
        geocoded = GeocodingResult(
            road_address=request.address.strip(),
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
        credits=0,
        daily_free_used=0,
        daily_free_reset_at=_bind_utc(db, next_daily_free_reset_at(now)),
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        if db.scalar(select(User.id).where(User.username == request.username)) is not None:
            raise DuplicateUsernameError from error
        if email is not None and db.scalar(select(User.id).where(User.email == email)) is not None:
            raise DuplicateEmailError from error
        raise
    db.refresh(user)
    return user


def authenticate_user(db: Session, username: str, password: str) -> User | None:
    """사용자명과 비밀번호가 일치하는 사용자를 반환합니다."""
    normalized = username.strip().lower()
    user = db.scalar(select(User).where(User.username == normalized))
    password_hash = user.password_hash if user is not None else _DUMMY_PASSWORD_HASH
    password_matches = verify_password(password, password_hash)
    if user is None or not password_matches:
        return None
    return user
