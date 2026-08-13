# cache/models.py — 컨설턴트 챗봇 담당자가 관리하는 캐시 ORM 모델
from datetime import datetime

from sqlalchemy import Float, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    """cache/ ORM 모델이 공통으로 상속하는 선언형 베이스.

    테이블 DDL은 캐시 소유자(컨설턴트)가 이 Base로 직접 생성한다(D-061, cache/db.py 참고).
    """


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


class TrendCache(Base):
    """트렌드 조회 결과 캐시 — trend_repo.get_trend()의 Cache-Aside 저장소.

    상권과 달리 원본이 아니라 계약 형식(keyword/direction/related/weather)으로
    가공까지 끝난 최종 결과를 그대로 캐싱한다 — get_trend()의 industry 인자가
    아직 결과에 영향을 주지 않아(TODO: 실제 쓰임이 정해지면 재검토), 상권처럼
    "원본은 공유, industry별로 매번 재계산"할 이유가 없기 때문이다.
    """

    __tablename__ = "trend_cache"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    keyword: Mapped[str] = mapped_column(String(255), nullable=False)
    result_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
