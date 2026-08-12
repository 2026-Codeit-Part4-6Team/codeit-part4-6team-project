# cache/models.py — 컨설턴트 챗봇 담당자가 관리하는 캐시 ORM 모델
from datetime import datetime

from sqlalchemy import Float, Integer, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    """cache/ ORM 모델이 공통으로 상속하는 선언형 베이스. 실제 테이블 DDL은 서비스 담당자가 생성한다."""


class MarketCache(Base):
    """상권 조회 결과 캐시 — market_repo.get_market()의 Cache-Aside 저장소 (서비스 계약 §4.7).

    TODO(섹션 5, market_repo 실구현 시): (lat, lng, radius) 조합에 UNIQUE 제약이
    없으면 같은 좌표로 여러 번 적재될 수 있다. 조회 시 created_at 기준 최신 행을
    선택하도록 구현할 것 — 서비스 담당자에게 UNIQUE/index 존재 여부 확인 필요.
    """

    __tablename__ = "market_cache"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    lat: Mapped[float] = mapped_column(Float, nullable=False)
    lng: Mapped[float] = mapped_column(Float, nullable=False)
    radius: Mapped[int] = mapped_column(Integer, nullable=False)
    result_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
