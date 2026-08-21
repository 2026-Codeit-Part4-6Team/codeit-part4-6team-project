from sqlalchemy import inspect

from backend.database import create_database_engine
from backend.init_db import create_tables


def test_sqlite_foreign_keys_are_enabled(tmp_path):
    """SQLite 연결은 외래 키 제약을 활성화합니다."""
    engine = create_database_engine(f"sqlite:///{tmp_path / 'test.db'}")

    with engine.connect() as connection:
        enabled = connection.exec_driver_sql("PRAGMA foreign_keys").scalar_one()

    assert enabled == 1


def test_init_db_creates_only_service_tables(tmp_path):
    """서비스 초기화는 서비스 소유 테이블 네 개만 생성합니다."""
    engine = create_database_engine(f"sqlite:///{tmp_path / 'test.db'}")

    create_tables(engine)

    assert set(inspect(engine).get_table_names()) == {
        "users",
        "payments",
        "generations",
        "waiting_copies",
    }


def test_file_sqlite_uses_wal(tmp_path):
    engine = create_database_engine(f"sqlite:///{tmp_path / 'wal.db'}")
    with engine.connect() as connection:
        mode = connection.exec_driver_sql("PRAGMA journal_mode").scalar_one()
    assert mode.lower() == "wal"
    engine.dispose()


def test_memory_sqlite_does_not_require_wal():
    engine = create_database_engine("sqlite:///:memory:")
    with engine.connect() as connection:
        mode = connection.exec_driver_sql("PRAGMA journal_mode").scalar_one()
    assert mode.lower() != "wal"
    engine.dispose()


def test_test_settings_never_point_at_dev_database():
    from backend.config import settings

    assert "data/app.db" not in settings.database_url.replace("\\", "/")


def test_sqlite_connection_uses_30_second_busy_timeout(tmp_path):
    engine = create_database_engine(f"sqlite:///{tmp_path / 'timeout.db'}")
    with engine.connect() as connection:
        timeout_ms = connection.exec_driver_sql("PRAGMA busy_timeout").scalar_one()
    assert timeout_ms == 30_000
    engine.dispose()
