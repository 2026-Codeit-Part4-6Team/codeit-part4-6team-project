# cache/market_repo.py — Cache-Aside 동작 테스트
import json
import logging
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from cache.market_repo import get_market
from cache.models import Base, MarketCache

_STORES = [
    {
        "indsLclsNm": "음식점",
        "indsMclsNm": "카페",
        "indsSclsNm": "커피전문점",
        "lat": 37.4981,
        "lon": 127.0277,
    },
    {
        "indsLclsNm": "소매업",
        "indsMclsNm": "편의점",
        "indsSclsNm": "편의점",
        "lat": 37.4982,
        "lon": 127.0278,
    },
]


@pytest.fixture
def session_factory(monkeypatch):
    """테스트마다 독립된 인메모리 SQLite로 SessionLocal을 교체한다."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    monkeypatch.setattr("cache.market_repo.SessionLocal", factory)
    return factory


@patch("cache.market_repo.fetch_raw")
def test_cache_miss_fetches_and_stores(mock_fetch_raw, session_factory) -> None:
    mock_fetch_raw.return_value = (_STORES, 2)

    result = get_market(37.4980, 127.0276, industry="카페")

    mock_fetch_raw.assert_called_once_with(37.4980, 127.0276, 500)
    assert result["total_count"] == 2
    assert result["same_industry_count"] == 1

    with session_factory() as session:
        row = session.query(MarketCache).one()
        assert row.lat == pytest.approx(37.498)
        assert row.lng == pytest.approx(127.028)
        cached = json.loads(row.result_json)
        assert cached["total_count"] == 2
        assert len(cached["stores"]) == 2


@patch("cache.market_repo.fetch_raw")
def test_cache_hit_does_not_call_fetch_raw(mock_fetch_raw, session_factory) -> None:
    with session_factory() as session:
        session.add(
            MarketCache(
                lat=37.498,
                lng=127.028,
                radius=500,
                result_json=json.dumps({"stores": _STORES, "total_count": 2}),
            )
        )
        session.commit()

    result = get_market(37.4980, 127.0276, industry="카페")

    mock_fetch_raw.assert_not_called()
    assert result["total_count"] == 2
    assert result["same_industry_count"] == 1


@patch("cache.market_repo.fetch_raw")
def test_cache_expired_refetches(mock_fetch_raw, session_factory) -> None:
    old_time = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=8)
    with session_factory() as session:
        session.add(
            MarketCache(
                lat=37.498,
                lng=127.028,
                radius=500,
                result_json=json.dumps({"stores": [], "total_count": 0}),
                created_at=old_time,
            )
        )
        session.commit()
    mock_fetch_raw.return_value = (_STORES, 2)

    result = get_market(37.4980, 127.0276, industry="카페")

    mock_fetch_raw.assert_called_once()
    assert result["total_count"] == 2


@patch("cache.market_repo.fetch_raw")
def test_fetch_raw_failure_returns_none(mock_fetch_raw, session_factory) -> None:
    mock_fetch_raw.return_value = None

    result = get_market(37.4980, 127.0276)

    assert result is None
    with session_factory() as session:
        assert session.query(MarketCache).count() == 0


@patch("cache.market_repo.fetch_raw")
def test_different_industries_share_cache(mock_fetch_raw, session_factory) -> None:
    """같은 좌표는 industry가 달라도 원본 캐시를 재사용해야 한다(캐시 미스 1회만)."""
    mock_fetch_raw.return_value = (_STORES, 2)

    first = get_market(37.4980, 127.0276, industry="카페")
    second = get_market(37.4980, 127.0276, industry="편의점")

    mock_fetch_raw.assert_called_once()
    assert first["same_industry_count"] == 1
    assert second["same_industry_count"] == 1


@patch("cache.market_repo.fetch_raw")
def test_nearby_coordinates_share_cache_via_rounding(mock_fetch_raw, session_factory) -> None:
    """좌표를 소수 3자리로 반올림해 같은 캐시 키로 묶인다(약 100m 단위)."""
    mock_fetch_raw.return_value = (_STORES, 2)

    get_market(37.49801, 127.02761)
    get_market(37.49802, 127.02763)

    mock_fetch_raw.assert_called_once()


@patch("cache.market_repo.fetch_raw")
def test_db_failure_falls_back_to_live_fetch_without_crashing(mock_fetch_raw, monkeypatch) -> None:
    """캐시 DB 조회·적재가 모두 실패해도 예외를 삼키고 실시간 API 결과를 반환한다."""
    broken_factory = sessionmaker(bind=create_engine("sqlite:////nonexistent_dir_xyz/cache.db"))
    monkeypatch.setattr("cache.market_repo.SessionLocal", broken_factory)
    mock_fetch_raw.return_value = (_STORES, 2)

    result = get_market(37.4980, 127.0276, industry="카페")

    assert result is not None
    assert result["total_count"] == 2
    assert result["same_industry_count"] == 1


@patch("cache.market_repo.fetch_raw")
def test_corrupted_cache_json_falls_back_to_live_fetch(mock_fetch_raw, session_factory) -> None:
    """저장된 result_json이 파싱 자체가 안 되면 예외 없이 캐시 미스로 처리한다."""
    with session_factory() as session:
        session.add(
            MarketCache(lat=37.498, lng=127.028, radius=500, result_json="not-json{")
        )
        session.commit()
    mock_fetch_raw.return_value = (_STORES, 2)

    result = get_market(37.4980, 127.0276, industry="카페")

    mock_fetch_raw.assert_called_once()
    assert result["total_count"] == 2


@pytest.mark.parametrize(
    "malformed_payload",
    [
        {"stores": None, "total_count": 2},
        {"stores": _STORES, "total_count": "2"},
        {"stores": _STORES, "total_count": True},
        {"stores": ["not-a-dict"], "total_count": 2},
        {"stores": _STORES},
        {"total_count": 2},
        ["stores", "total_count"],
        "그냥 문자열",
    ],
)
@patch("cache.market_repo.fetch_raw")
def test_cache_with_wrong_shape_falls_back_to_live_fetch(
    mock_fetch_raw, session_factory, malformed_payload
) -> None:
    """JSON 파싱은 성공했지만 기대한 형태(stores: list[dict], total_count: int)가 아니면 미스로 처리한다."""
    with session_factory() as session:
        session.add(
            MarketCache(
                lat=37.498, lng=127.028, radius=500, result_json=json.dumps(malformed_payload)
            )
        )
        session.commit()
    mock_fetch_raw.return_value = (_STORES, 2)

    result = get_market(37.4980, 127.0276, industry="카페")

    mock_fetch_raw.assert_called_once()
    assert result["total_count"] == 2


@patch("cache.market_repo.fetch_raw")
def test_cache_hit_is_logged(mock_fetch_raw, session_factory, caplog) -> None:
    with session_factory() as session:
        session.add(
            MarketCache(
                lat=37.498,
                lng=127.028,
                radius=500,
                result_json=json.dumps({"stores": _STORES, "total_count": 2}),
            )
        )
        session.commit()

    with caplog.at_level(logging.INFO, logger="cache.market_repo"):
        get_market(37.4980, 127.0276, industry="카페")

    assert any(
        record.levelno == logging.INFO and "cache hit" in record.message
        for record in caplog.records
    )


@patch("cache.market_repo.fetch_raw")
def test_cache_miss_is_logged(mock_fetch_raw, session_factory, caplog) -> None:
    mock_fetch_raw.return_value = (_STORES, 2)

    with caplog.at_level(logging.INFO, logger="cache.market_repo"):
        get_market(37.4980, 127.0276, industry="카페")

    assert any(
        record.levelno == logging.INFO and "cache miss" in record.message
        for record in caplog.records
    )


@patch("cache.market_repo.fetch_raw")
def test_db_read_failure_logs_warning(mock_fetch_raw, monkeypatch, caplog) -> None:
    broken_factory = sessionmaker(bind=create_engine("sqlite:////nonexistent_dir_xyz/cache.db"))
    monkeypatch.setattr("cache.market_repo.SessionLocal", broken_factory)
    mock_fetch_raw.return_value = (_STORES, 2)

    with caplog.at_level(logging.WARNING, logger="cache.market_repo"):
        get_market(37.4980, 127.0276, industry="카페")

    assert any(
        record.levelno == logging.WARNING and "cache read failed" in record.message
        for record in caplog.records
    )
    # API 키·응답 원문이 로그에 남지 않아야 한다
    logged_text = " ".join(record.message for record in caplog.records)
    assert "MARKET_API_KEY" not in logged_text
