# cache/db.py 테스트 — DATABASE_URL 설정 여부와 무관하게 캐시 테이블이 생성되는지 확인(D-061)
import importlib
from contextlib import contextmanager

import pytest
from sqlalchemy import create_engine, inspect, text

import cache.db as cache_db


@contextmanager
def _database_url_set_to(url: str):
    """DATABASE_URL을 임시로 바꾸고 cache.db를 리로드한 뒤, 블록이 끝나면 원래
    환경변수 값으로 복원하고 다시 리로드한다.

    monkeypatch만 쓰면 테스트 종료(fixture teardown) 시 환경변수는 원래 값으로
    돌아오지만, 그 시점엔 이미 테스트 안에서 실행한 importlib.reload가 끝난
    뒤라 cache_db._engine 등 모듈 객체는 그대로 남는다(원래 DATABASE_URL이
    설정돼 있던 환경이면 특히 문제). pytest.MonkeyPatch()를 직접 만들어
    try/finally로 감싸, yield한 블록 안에서 예외(assert 실패 등)가 나도
    "환경변수 복원 → 한 번 더 reload"가 항상 실행되게 한다 — with 블록
    안에서 yield하면 예외가 바깥 with의 __exit__ 이후 코드를 건너뛴다.
    """
    mp = pytest.MonkeyPatch()
    try:
        mp.setenv("DATABASE_URL", url)
        importlib.reload(cache_db)
        yield cache_db
    finally:
        mp.undo()
        importlib.reload(cache_db)


def test_creates_cache_tables_even_when_database_url_is_set(tmp_path) -> None:
    """DATABASE_URL이 설정된 실제 배포 환경을 흉내내도 market_cache/trend_cache
    테이블이 실제로 생성돼야 한다. 그렇지 않으면 모든 캐시 조회·적재가 조용히
    실패해(테이블 없음) 매번 실시간 API를 호출하게 되고, TTL·월 5만 건 한도
    방어가 전부 무력화된다."""
    db_path = tmp_path / "test_cache.db"

    with _database_url_set_to(f"sqlite:///{db_path}") as reloaded:
        table_names = inspect(reloaded._engine).get_table_names()

        assert "market_cache" in table_names
        assert "trend_cache" in table_names


def test_adds_industry_code_column_to_pre_existing_market_cache_table(tmp_path) -> None:
    """create_all()은 이미 존재하는 테이블에 새 컬럼을 추가하지 않는다 — market_cache에
    industry_code 컬럼이 나중에(D-041/D-042) 추가됐으므로, 구버전 스키마로 이미
    만들어진 DB를 그대로 열면 'no such column: market_cache.industry_code' 오류로
    캐시 조회·적재가 전부 실패한다(Codex 리뷰에서 실제 재현). cache.db가 직접
    컬럼 존재를 확인해 보정해야 한다."""
    db_path = tmp_path / "legacy.db"
    old_engine = create_engine(f"sqlite:///{db_path}")
    with old_engine.begin() as conn:
        conn.execute(
            text(
                "CREATE TABLE market_cache ("
                "id INTEGER PRIMARY KEY AUTOINCREMENT, "
                "lat FLOAT NOT NULL, lng FLOAT NOT NULL, radius INTEGER NOT NULL, "
                "result_json TEXT NOT NULL, "
                "created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP)"
            )
        )
    old_engine.dispose()

    with _database_url_set_to(f"sqlite:///{db_path}") as reloaded:
        columns = {col["name"] for col in inspect(reloaded._engine).get_columns("market_cache")}
        assert "industry_code" in columns


def test_sqlite_uses_wal_and_30s_busy_timeout(tmp_path) -> None:
    """D-062: 서비스(generations)와 컨설턴트(market_cache)가 같은 SQLite 파일에
    동시에 쓸 때 'database is locked'가 나지 않으려면 WAL 모드 + 30초 대기가
    필요하다."""
    db_path = tmp_path / "test_wal.db"

    with _database_url_set_to(f"sqlite:///{db_path}") as reloaded:
        with reloaded._engine.connect() as conn:
            journal_mode = conn.exec_driver_sql("PRAGMA journal_mode").scalar()
            busy_timeout = conn.exec_driver_sql("PRAGMA busy_timeout").scalar()

        assert journal_mode == "wal"
        assert busy_timeout == 30000


def test_import_succeeds_when_db_unreachable() -> None:
    """DB 자체에 연결할 수 없어도(create_all 실패) 모듈 import는 성공해야 한다.

    여기서 예외가 그대로 올라가면 cache.db를 import하는 market_repo.py/
    trend_repo.py까지 import가 통째로 실패해서, get_trend()/get_market()의
    실시간 API 폴백 로직 자체에 도달하지 못한다."""
    with _database_url_set_to("sqlite:////nonexistent_dir_xyz/cache.db") as reloaded:
        assert reloaded.SessionLocal is not None
