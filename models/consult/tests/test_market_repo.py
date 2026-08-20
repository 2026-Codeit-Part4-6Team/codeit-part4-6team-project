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


@pytest.fixture(autouse=True)
def _default_fetch_by_code_fails(monkeypatch):
    """명시적으로 다르게 mock하지 않는 한, 업종코드 필터 호출(D-041/D-042)은
    실패(None)로 취급해 이 파일의 기존 텍스트 매칭 기반 테스트들이 그 경로를
    그대로 검증하게 한다. 업종코드 필터 경로 자체를 검증하는 테스트는 개별적으로
    다시 patch한다."""
    monkeypatch.setattr("cache.market_repo.fetch_by_code", lambda *args, **kwargs: None)


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
def test_picks_latest_row_when_created_at_ties(mock_fetch_raw, session_factory) -> None:
    """SQLite CURRENT_TIMESTAMP는 초 단위라 짧은 시간에 여러 번 적재되면 created_at이
    같을 수 있다 — 이때도 id 기준으로 가장 최신(나중에 적재된) 행을 골라야 한다."""
    same_time = datetime.now(UTC).replace(tzinfo=None)
    older_payload = {"stores": [], "total_count": 1}
    newer_payload = {"stores": _STORES, "total_count": 2}
    with session_factory() as session:
        session.add(
            MarketCache(
                lat=37.498, lng=127.028, radius=500,
                result_json=json.dumps(older_payload), created_at=same_time,
            )
        )
        session.add(
            MarketCache(
                lat=37.498, lng=127.028, radius=500,
                result_json=json.dumps(newer_payload), created_at=same_time,
            )
        )
        session.commit()

    result = get_market(37.4980, 127.0276, industry="카페")

    mock_fetch_raw.assert_not_called()
    assert result["total_count"] == 2


@patch("cache.market_repo.fetch_raw")
def test_repeated_cache_miss_upserts_instead_of_inserting_new_row(
    mock_fetch_raw, session_factory
) -> None:
    """같은 (lat,lng,radius)로 반복 적재되면 새 행을 계속 추가하는 대신 기존 행을
    갱신한다(D-053) — UNIQUE 인덱스는 아직 없어(D7에 서비스 담당이 추가 예정) DB가
    직접 중복을 막아주지 않으므로, upsert로 미리 방어한다."""
    mock_fetch_raw.return_value = (_STORES, 2)
    get_market(37.4980, 127.0276, industry="카페")
    with session_factory() as session:
        assert session.query(MarketCache).count() == 1

    with session_factory() as session:
        row = session.query(MarketCache).one()
        row.created_at = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=8)
        session.commit()

    mock_fetch_raw.return_value = ([], 0)
    get_market(37.4980, 127.0276, industry="카페")

    with session_factory() as session:
        assert session.query(MarketCache).count() == 1
        row = session.query(MarketCache).one()
        assert json.loads(row.result_json)["total_count"] == 0


@patch("cache.market_repo.fetch_by_code")
@patch("cache.market_repo.fetch_raw")
def test_uses_industry_code_filter_when_mapping_exists(
    mock_fetch_raw, mock_fetch_by_code, session_factory
) -> None:
    """"카페"는 industry_code_for()로 코드(I21201)를 찾을 수 있으므로, fetch_by_code()로
    필터링된 결과의 totalCount를 same_industry_count로 쓴다(텍스트 매칭 결과인 1이 아님)."""
    mock_fetch_raw.return_value = (_STORES, 2)
    mock_fetch_by_code.return_value = ([_STORES[0]], 177)

    result = get_market(37.4980, 127.0276, industry="카페")

    mock_fetch_by_code.assert_called_once_with(37.4980, 127.0276, 500, "I21201")
    assert result["same_industry_count"] == 177


@patch("cache.market_repo.fetch_by_code")
@patch("cache.market_repo.fetch_raw")
def test_industry_code_cache_hit_does_not_call_fetch_by_code_again(
    mock_fetch_raw, mock_fetch_by_code, session_factory
) -> None:
    mock_fetch_raw.return_value = (_STORES, 2)
    with session_factory() as session:
        session.add(
            MarketCache(
                lat=37.498,
                lng=127.028,
                radius=500,
                industry_code="I21201",
                result_json=json.dumps({"stores": [_STORES[0]], "total_count": 177}),
            )
        )
        session.commit()

    result = get_market(37.4980, 127.0276, industry="카페")

    mock_fetch_by_code.assert_not_called()
    assert result["same_industry_count"] == 177


@patch("cache.market_repo.fetch_by_code")
@patch("cache.market_repo.fetch_raw")
def test_industry_code_cache_is_independent_from_raw_cache(
    mock_fetch_raw, mock_fetch_by_code, session_factory
) -> None:
    """원본(업종 무관) 캐시와 업종코드 필터 캐시는 별도 행으로 저장된다."""
    mock_fetch_raw.return_value = (_STORES, 2)
    mock_fetch_by_code.return_value = ([_STORES[0]], 177)

    get_market(37.4980, 127.0276, industry="카페")

    with session_factory() as session:
        rows = session.query(MarketCache).all()
        assert len(rows) == 2
        assert {row.industry_code for row in rows} == {None, "I21201"}


@patch("cache.market_repo.fetch_raw")
def test_upsert_refreshes_ttl_even_when_payload_is_identical(mock_fetch_raw, session_factory) -> None:
    """만료된 캐시를 재적재할 때 새로 받아온 값이 기존 값과 동일해도 created_at이
    갱신돼야 한다 — SQLAlchemy는 값이 바뀌지 않은 컬럼은 UPDATE 대상으로 보지
    않아 onupdate=func.now()가 발동하지 않는다. 갱신이 안 되면 다음 조회도
    여전히 만료로 판정돼 매번 실시간 API를 다시 호출하게 된다."""
    old_time = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=8)
    with session_factory() as session:
        session.add(
            MarketCache(
                lat=37.498,
                lng=127.028,
                radius=500,
                result_json=json.dumps({"stores": _STORES, "total_count": 2}),
                created_at=old_time,
            )
        )
        session.commit()
    mock_fetch_raw.return_value = (_STORES, 2)  # 기존 캐시와 동일한 payload

    get_market(37.4980, 127.0276)

    with session_factory() as session:
        row = session.query(MarketCache).one()
        assert row.created_at > old_time + timedelta(days=7)


@patch("cache.market_repo.fetch_by_code")
@patch("cache.market_repo.fetch_raw")
def test_falls_back_to_text_matching_when_fetch_by_code_fails(
    mock_fetch_raw, mock_fetch_by_code, session_factory
) -> None:
    mock_fetch_raw.return_value = (_STORES, 2)
    mock_fetch_by_code.return_value = None

    result = get_market(37.4980, 127.0276, industry="카페")

    assert result["same_industry_count"] == 1


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
