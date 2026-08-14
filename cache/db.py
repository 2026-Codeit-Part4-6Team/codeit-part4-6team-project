# cache/db.py — cache/ 리포지토리가 공용으로 쓰는 DB 세션 팩토리
import logging
import os

from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker

from cache.models import Base

logger = logging.getLogger(__name__)

_database_url = os.getenv("DATABASE_URL")

if _database_url:
    _engine = create_engine(_database_url)
else:
    # DATABASE_URL 미설정 시 로컬 SQLite 파일로 폴백한다.
    _engine = create_engine("sqlite:///./cache.db")

if _engine.url.get_backend_name() == "sqlite":
    # D-062: 서비스(generations)와 컨설턴트(market_cache/trend_cache)가 같은 SQLite
    # 파일에 동시에 쓸 수 있어, 기본 설정(journal_mode=delete, busy_timeout≈5초)로는
    # "database is locked"가 날 수 있다. WAL은 읽기와 쓰기가 서로 안 막게 해주고,
    # 30초 대기는 그래도 겹치는 순간의 오류를 재시도 없이 흡수한다.
    @event.listens_for(_engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, connection_record) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=30000")
        cursor.close()

# 캐시 테이블은 소유자(컨설턴트)가 자기 Base로 생성한다(D-061) — DATABASE_URL이
# 설정된 실제 배포 환경에서도 서비스 쪽 init_db가 market_cache/trend_cache를
# 모르면 테이블이 아예 없어, 모든 캐시 조회·적재가 조용히 실패하고 매번 실시간
# API를 호출하게 된다(TTL·월 5만 건 한도 방어 무력화). 이미 존재하는 테이블은
# create_all()이 건너뛰므로 서비스 쪽 마이그레이션과 충돌하지 않는다.
#
# DB에 연결 자체가 안 되는 경우(네트워크 장애 등)에도 예외를 삼켜 모듈 import는
# 항상 성공하게 한다 — 여기서 예외가 그대로 올라가면 이 모듈을 import하는
# market_repo.py/trend_repo.py까지 import가 통째로 실패해, "캐시 DB 장애 시
# 실시간 API로 폴백한다"는 Cache-Aside 원칙 자체가 깨진다.
def _ensure_market_cache_industry_code_column(engine) -> None:
    """create_all()은 이미 존재하는 테이블에 새 컬럼을 추가하지 않는다.

    market_cache에 industry_code 컬럼이 나중에(D-041/D-042) 추가됐으므로, 구버전
    스키마로 이미 만들어진 DB(로컬 개발 DB, 먼저 배포된 환경 등)를 그대로 열면
    "no such column: market_cache.industry_code" 오류로 캐시 조회·적재가 전부
    실패한다(Codex 리뷰에서 실제 재현). 이 프로젝트는 Alembic을 쓰지 않기로
    했으므로(D-067) 여기서 직접 컬럼 존재를 확인해 없으면 추가한다.
    """
    inspector = inspect(engine)
    if "market_cache" not in inspector.get_table_names():
        return
    columns = {col["name"] for col in inspector.get_columns("market_cache")}
    if "industry_code" in columns:
        return
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE market_cache ADD COLUMN industry_code VARCHAR(20)"))


try:
    Base.metadata.create_all(_engine)
    _ensure_market_cache_industry_code_column(_engine)
except SQLAlchemyError:
    logger.warning("cache table creation failed, continuing without cache tables")

SessionLocal = sessionmaker(bind=_engine)
