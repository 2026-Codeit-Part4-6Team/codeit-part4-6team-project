import math
import os
from dataclasses import dataclass


def _read_int(name: str, default: int, *, minimum: int = 0) -> int:
    """환경변수 정수를 읽고 최소값을 검증합니다."""
    value = int(os.getenv(name, str(default)))
    if value < minimum:
        raise ValueError(f"{name}은 {minimum} 이상이어야 합니다.")
    return value


def _read_bool(name: str, default: bool) -> bool:
    """환경변수 boolean을 읽습니다."""
    raw = os.getenv(name, str(default)).strip().lower()
    if raw not in {"true", "false"}:
        raise ValueError(f"{name}은 true 또는 false여야 합니다.")
    return raw == "true"


def _read_coordinate(name: str, default: float, *, minimum: float, maximum: float) -> float:
    """환경변수 좌표를 유한한 허용 범위로 읽습니다."""
    value = float(os.getenv(name, str(default)))
    if not math.isfinite(value) or not minimum <= value <= maximum:
        raise ValueError(f"{name} 좌표는 {minimum}에서 {maximum} 사이의 유한값이어야 합니다.")
    return value


@dataclass(frozen=True)
class Settings:
    """서비스 실행 설정."""

    database_url: str
    daily_free_limit: int
    basic_credit_cost: int
    consultant_credit_cost: int
    model_request_timeout_seconds: int
    chatbot_mode: str
    session_secret_key: str
    session_max_age_seconds: int
    session_cookie_secure: bool
    naver_maps_api_key_id: str
    naver_maps_api_key: str
    geocode_fallback_enabled: bool
    geocode_fallback_lat: float
    geocode_fallback_lng: float


def load_settings() -> Settings:
    """환경변수에서 서비스 설정을 생성합니다."""
    environment = os.getenv("APP_ENV", "development").strip().lower()
    if environment not in {"development", "test", "demo", "production"}:
        raise ValueError("APP_ENV는 development, test, demo, production 중 하나여야 합니다.")
    geocode_fallback_enabled = _read_bool("GEOCODE_FALLBACK_ENABLED", False)
    if environment not in {"development", "demo"} and geocode_fallback_enabled:
        raise ValueError("geocoding fallback은 development 또는 demo 환경에서만 사용할 수 있습니다.")
    secret_key = os.getenv("SESSION_SECRET_KEY")
    if secret_key is not None:
        secret_key = secret_key.strip()
    session_cookie_secure = _read_bool("SESSION_COOKIE_SECURE", False)
    if environment == "production":
        if not secret_key or secret_key in {
            "local-development-secret",
            "change-this-in-real-environments",
        }:
            raise ValueError("운영 환경에서는 SESSION_SECRET_KEY가 필요합니다.")
        if not session_cookie_secure:
            raise ValueError("운영 환경에서는 SESSION_COOKIE_SECURE=true가 필요합니다.")
    else:
        secret_key = secret_key or "local-development-secret"
    chatbot_mode = os.getenv("CHATBOT_MODE", "mock").strip().lower()
    if chatbot_mode not in {"mock", "actual"}:
        raise ValueError("CHATBOT_MODE는 mock 또는 actual이어야 합니다.")
    return Settings(
        database_url=os.getenv("DATABASE_URL", "sqlite:///./data/app.db"),
        daily_free_limit=_read_int("DAILY_FREE_LIMIT", 10),
        basic_credit_cost=_read_int("BASIC_CREDIT_COST", 50),
        consultant_credit_cost=_read_int("CONSULTANT_CREDIT_COST", 10),
        model_request_timeout_seconds=_read_int(
            "MODEL_REQUEST_TIMEOUT_SECONDS", 60, minimum=60
        ),
        chatbot_mode=chatbot_mode,
        session_secret_key=secret_key,
        session_max_age_seconds=_read_int("SESSION_MAX_AGE_SECONDS", 28_800, minimum=1),
        session_cookie_secure=session_cookie_secure,
        naver_maps_api_key_id=os.getenv("NAVER_MAPS_API_KEY_ID", ""),
        naver_maps_api_key=os.getenv("NAVER_MAPS_API_KEY", ""),
        geocode_fallback_enabled=geocode_fallback_enabled,
        geocode_fallback_lat=_read_coordinate(
            "GEOCODE_FALLBACK_LAT", 37.4979, minimum=-90, maximum=90
        ),
        geocode_fallback_lng=_read_coordinate(
            "GEOCODE_FALLBACK_LNG", 127.0276, minimum=-180, maximum=180
        ),
    )


settings = load_settings()
