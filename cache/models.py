# cache/models.py — 컨설턴트 챗봇 담당자가 관리하는 캐시 ORM 모델
from datetime import datetime

from sqlalchemy import CheckConstraint, Float, Integer, String, Text
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
    __table_args__ = (
        CheckConstraint("lat BETWEEN -90 AND 90", name="ck_market_cache_lat"),
        CheckConstraint("lng BETWEEN -180 AND 180", name="ck_market_cache_lng"),
        CheckConstraint("radius > 0", name="ck_market_cache_radius"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    lat: Mapped[float] = mapped_column(Float, nullable=False)
    lng: Mapped[float] = mapped_column(Float, nullable=False)
    radius: Mapped[int] = mapped_column(Integer, nullable=False)
    result_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)


class TrendCache(Base):
    """검색어 트렌드 원본 캐시입니다."""

    __tablename__ = "trend_cache"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    keyword: Mapped[str] = mapped_column(String(200), nullable=False)
    industry: Mapped[str | None] = mapped_column(String(100), nullable=True)
    direction: Mapped[str] = mapped_column(String(20), nullable=False)
    related_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]", server_default="[]")
    weather_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)


class ReviewCache(Base):
    """사전 수집한 경쟁사 리뷰 요약 캐시입니다."""

    __tablename__ = "review_cache"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    place_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    review_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    sentiment_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    num_reviews: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    crawled_at: Mapped[datetime | None] = mapped_column(nullable=True)


class BannedKeyword(Base):
    """PM이 관리하는 금지·주의 키워드 사전 저장소입니다."""

    __tablename__ = "banned_keywords"
    __table_args__ = (
        CheckConstraint("action IN ('block', 'reask', 'warn')", name="ck_banned_keywords_action"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    keyword: Mapped[str] = mapped_column(String(100), nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    action: Mapped[str] = mapped_column(String(20), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
