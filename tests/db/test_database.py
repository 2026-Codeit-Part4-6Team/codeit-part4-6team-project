from sqlalchemy import inspect
from sqlalchemy.orm import Session

from backend.database import create_database_engine
from backend.init_db import create_tables
from backend.models import Generation, User


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


def test_init_db_upgrades_legacy_generation_platform_constraint(tmp_path):
    """기존 DB의 instagram/banner 제약을 xbanner까지 확장하고 데이터를 보존합니다."""
    engine = create_database_engine(f"sqlite:///{tmp_path / 'legacy.db'}")
    with engine.begin() as connection:
        connection.exec_driver_sql(
            """
            CREATE TABLE generations (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                source_gen_id INTEGER,
                chatbot_type VARCHAR(20) NOT NULL,
                idempotency_key VARCHAR(36) NOT NULL,
                request_hash VARCHAR(64) NOT NULL,
                title TEXT,
                question TEXT NOT NULL,
                platform VARCHAR(20) CHECK (
                    platform IS NULL OR platform IN ('instagram', 'banner')
                ),
                copy_content TEXT,
                image_path TEXT,
                image_b64 TEXT,
                result_json TEXT,
                plan VARCHAR(10) NOT NULL,
                credits_used INTEGER NOT NULL DEFAULT 0,
                tokens_used INTEGER NOT NULL DEFAULT 0,
                status VARCHAR(20) NOT NULL DEFAULT 'pending',
                hitl_approved BOOLEAN NOT NULL DEFAULT 0,
                selected_proposal_index INTEGER,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        connection.exec_driver_sql(
            """
            INSERT INTO generations (
                id, user_id, chatbot_type, idempotency_key, request_hash,
                question, platform, plan
            ) VALUES (1, 1, 'basic',
                '00000000-0000-0000-0000-000000000001',
                printf('%064d', 0), '기존 인스타 문구', 'banner', 'free')
            """
        )

    create_tables(engine)

    with Session(engine) as session:
        user = User(id=1, username="legacy-owner", password_hash="bcrypt-hash")
        session.add(user)
        session.flush()
        session.add(
            Generation(
                user_id=user.id,
                chatbot_type="basic",
                idempotency_key="00000000-0000-0000-0000-000000000002",
                request_hash="b" * 64,
                question="X배너 문구",
                platform="xbanner",
                plan="free",
            )
        )
        session.commit()
        platforms = [row[0] for row in session.query(Generation.platform).all()]

    assert set(platforms) == {"banner", "xbanner"}
