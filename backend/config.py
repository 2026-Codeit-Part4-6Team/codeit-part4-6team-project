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


@dataclass(frozen=True)
class Settings:
    """서비스 실행 설정."""

    database_url: str
    daily_free_limit: int
    basic_credit_cost: int
    consultant_credit_cost: int
    model_request_timeout_seconds: int
    session_secret_key: str
    session_max_age_seconds: int
    session_cookie_secure: bool
    naver_maps_api_key_id: str
    naver_maps_api_key: str


def load_settings() -> Settings:
    """환경변수에서 서비스 설정을 생성합니다."""
    return Settings(
        database_url=os.getenv("DATABASE_URL", "sqlite:///./data/app.db"),
        daily_free_limit=_read_int("DAILY_FREE_LIMIT", 10),
        basic_credit_cost=_read_int("BASIC_CREDIT_COST", 10),
        consultant_credit_cost=_read_int("CONSULTANT_CREDIT_COST", 50),
        model_request_timeout_seconds=_read_int(
            "MODEL_REQUEST_TIMEOUT_SECONDS", 60, minimum=60
        ),
        session_secret_key=os.getenv("SESSION_SECRET_KEY", "local-development-secret"),
        session_max_age_seconds=_read_int("SESSION_MAX_AGE_SECONDS", 28_800, minimum=1),
        session_cookie_secure=_read_bool("SESSION_COOKIE_SECURE", False),
        naver_maps_api_key_id=os.getenv("NAVER_MAPS_API_KEY_ID", ""),
        naver_maps_api_key=os.getenv("NAVER_MAPS_API_KEY", ""),
    )


settings = load_settings()
