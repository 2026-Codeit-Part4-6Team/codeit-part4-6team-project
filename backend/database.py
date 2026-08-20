from collections.abc import Generator

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker

from backend.config import settings


def create_database_engine(url: str) -> Engine:
    """서비스 DB Engine을 생성합니다."""
    connect_args = (
        {"check_same_thread": False, "timeout": 30}
        if url.startswith("sqlite")
        else {}
    )
    engine = create_engine(url, connect_args=connect_args)

    if url.startswith("sqlite"):
        parsed_url = make_url(url)
        use_wal = parsed_url.database not in (None, "", ":memory:")

        @event.listens_for(engine, "connect")
        def configure_sqlite_connection(dbapi_connection, _connection_record) -> None:
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA busy_timeout=30000")
            if use_wal:
                cursor.execute("PRAGMA journal_mode=WAL")
            cursor.close()

    return engine


engine = create_database_engine(settings.database_url)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    """요청 범위에서 사용할 DB Session을 제공합니다."""
    with SessionLocal() as session:
        yield session
