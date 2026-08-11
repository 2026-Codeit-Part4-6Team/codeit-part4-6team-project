import os
from dataclasses import dataclass


def _read_int(name: str, default: int, *, minimum: int = 0) -> int:
    """환경변수 정수를 읽고 최소값을 검증합니다."""
    value = int(os.getenv(name, str(default)))
    if value < minimum:
        raise ValueError(f"{name}은 {minimum} 이상이어야 합니다.")
    return value


@dataclass(frozen=True)
class Settings:
    """서비스 실행 설정."""

    database_url: str
    daily_free_limit: int
    basic_credit_cost: int
    consultant_credit_cost: int
    model_request_timeout_seconds: int


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
    )


settings = load_settings()
