from pathlib import Path

from sqlalchemy import Engine

from backend.config import settings
from backend.database import engine
from backend.models import Base
from cache.models import Base as CacheBase


def _ensure_sqlite_parent(database_url: str) -> None:
    """파일 기반 SQLite DB의 상위 디렉터리를 생성합니다."""
    prefix = "sqlite:///"
    if database_url.startswith(prefix) and database_url != "sqlite:///:memory:":
        Path(database_url.removeprefix(prefix)).parent.mkdir(parents=True, exist_ok=True)


def create_tables(target_engine: Engine = engine) -> None:
    """서비스 테이블 4개와 모델 Cache 스키마를 생성합니다."""
    if target_engine is engine:
        _ensure_sqlite_parent(settings.database_url)
    Base.metadata.create_all(target_engine)
    CacheBase.metadata.create_all(target_engine)


if __name__ == "__main__":
    create_tables()
