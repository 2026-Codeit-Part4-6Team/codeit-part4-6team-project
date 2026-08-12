# MarketCache ORM 모델 테스트
from datetime import UTC, datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from cache.models import Base, MarketCache


def test_market_cache_round_trip() -> None:
    """MarketCache 행을 저장하고 그대로 조회할 수 있다."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)

    with Session() as session:
        session.add(
            MarketCache(lat=37.5, lng=127.0, radius=500, result_json='{"total_count": 40}')
        )
        session.commit()

        row = session.query(MarketCache).one()
        assert row.lat == 37.5
        assert row.lng == 127.0
        assert row.radius == 500
        assert row.result_json == '{"total_count": 40}'
        assert row.created_at is not None


def test_created_at_is_utc_not_local() -> None:
    """DB가 채운 created_at은 UTC 기준이라, 애플리케이션의 UTC now와 비슷해야 한다.

    로컬 시간(KST 등)과 비교하면 시차만큼 어긋나 cache/ttl.py의 TTL 판정이 일찍
    만료된 것처럼 계산된다.
    """
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)

    with Session() as session:
        session.add(MarketCache(lat=37.5, lng=127.0, radius=500, result_json="{}"))
        session.commit()
        row = session.query(MarketCache).one()

    utc_now = datetime.now(UTC).replace(tzinfo=None)
    assert abs((utc_now - row.created_at).total_seconds()) < 60
