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

    (lat, lng, radius)에 UNIQUE 제약은 아직 없다(D7에 서비스 담당이 DDL로 추가 예정,
    P-011) — 그전까지는 market_repo._write_cache()가 upsert로 중복 삽입을 막는다(D-053).

    industry_code가 NULL인 행은 원본(업종 무관, 반경 내 최대 1000곳) 캐시이고,
    값이 있는 행은 그 업종코드(indsSclsCd)로 필터링된 조회 결과 캐시다(D-041/D-042).
    같은 좌표라도 원본과 업종별 필터 결과는 서로 다른 캐시 항목으로 관리된다.
    """

    __tablename__ = "market_cache"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    lat: Mapped[float] = mapped_column(Float, nullable=False)
    lng: Mapped[float] = mapped_column(Float, nullable=False)
    radius: Mapped[int] = mapped_column(Integer, nullable=False)
    industry_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    result_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now(), nullable=False
    )


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
