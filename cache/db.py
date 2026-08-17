# cache/db.py — cache/ 리포지토리가 공용으로 쓰는 DB 세션 팩토리
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from cache.models import Base

_database_url = os.getenv("DATABASE_URL")

if _database_url:
    # 서비스 담당자가 만든 실제 DB — 테이블 DDL은 서비스 담당 영역이라 여기서 생성하지 않는다(SDP §2.2).
    _engine = create_engine(_database_url)
else:
    # DATABASE_URL 미설정 시 로컬 SQLite 파일로 폴백한다(SDP §9 R13:
    # 캐시 테이블 DDL 생성이 지연되면 로컬 테이블로 임시 생성 후 나중에 통합).
    _engine = create_engine("sqlite:///./cache.db")
    Base.metadata.create_all(_engine)

SessionLocal = sessionmaker(bind=_engine)
