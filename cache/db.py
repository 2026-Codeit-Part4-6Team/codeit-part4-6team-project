# cache/db.py — cache/ 리포지토리가 공용으로 쓰는 DB 세션 팩토리
import logging
import os

from sqlalchemy import create_engine
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
try:
    Base.metadata.create_all(_engine)
except SQLAlchemyError:
    logger.warning("cache table creation failed, continuing without cache tables")

SessionLocal = sessionmaker(bind=_engine)
