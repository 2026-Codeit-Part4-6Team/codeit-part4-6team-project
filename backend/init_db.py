from pathlib import Path

from sqlalchemy import Engine
from sqlalchemy.schema import CreateTable

from backend.config import settings
from backend.database import engine
from backend.models import Base, Generation


def _ensure_sqlite_parent(database_url: str) -> None:
    """파일 기반 SQLite DB의 상위 디렉터리를 생성합니다."""
    prefix = "sqlite:///"
    if database_url.startswith(prefix) and database_url != "sqlite:///:memory:":
        Path(database_url.removeprefix(prefix)).parent.mkdir(parents=True, exist_ok=True)


def create_tables(target_engine: Engine = engine) -> None:
    """서비스 소유 테이블 네 개를 생성합니다."""
    if target_engine is engine:
        _ensure_sqlite_parent(settings.database_url)
    Base.metadata.create_all(target_engine)
    _upgrade_generation_platform_constraint(target_engine)


def _upgrade_generation_platform_constraint(target_engine: Engine) -> None:
    """기존 SQLite generations 테이블의 xbanner 제약을 경량 보정합니다.

    ``create_all``은 이미 존재하는 테이블의 CHECK 제약을 갱신하지 않습니다.
    따라서 v0.3 시점의 ``instagram|banner`` 테이블은 코드가
    ``xbanner``를 허용해도 INSERT 단계에서 실패합니다. SQLite는 CHECK 제약
    자체를 ALTER할 수 없으므로 기존 컬럼과 데이터를 새 테이블로 옮깁니다.
    """
    if target_engine.dialect.name != "sqlite":
        return

    raw_connection = target_engine.raw_connection()
    try:
        cursor = raw_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=OFF")
        cursor.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='generations'"
        )
        row = cursor.fetchone()
        if row is None or "xbanner" in (row[0] or "").lower():
            raw_connection.commit()
            return

        create_sql = str(
            CreateTable(Generation.__table__).compile(dialect=target_engine.dialect)
        )
        create_sql = create_sql.replace(
            "CREATE TABLE generations",
            "CREATE TABLE generations__xbanner_migration",
            1,
        ).replace(
            "REFERENCES generations",
            "REFERENCES generations__xbanner_migration",
        )
        cursor.execute(create_sql)

        columns = ", ".join(f'"{column.name}"' for column in Generation.__table__.columns)
        cursor.execute(
            f'INSERT INTO "generations__xbanner_migration" ({columns}) '
            f'SELECT {columns} FROM "generations"'
        )
        cursor.execute("DROP TABLE generations")
        cursor.execute(
            'ALTER TABLE "generations__xbanner_migration" RENAME TO "generations"'
        )
        raw_connection.commit()
    except Exception:
        raw_connection.rollback()
        raise
    finally:
        raw_connection.close()


if __name__ == "__main__":
    create_tables()
