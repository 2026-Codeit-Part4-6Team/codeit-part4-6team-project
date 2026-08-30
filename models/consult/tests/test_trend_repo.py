# cache/trend_repo.py — Cache-Aside 동작 테스트
import json
import logging
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from cache.models import Base, TrendCache
from cache.trend_repo import get_trend

_TREND_RESULT = {
    "keyword": "아이스아메리카노",
    "direction": "상승",
    "related": ["냉커피", "여름음료"],
}


@pytest.fixture
def session_factory(monkeypatch):
    """테스트마다 독립된 인메모리 SQLite로 SessionLocal을 교체한다."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    monkeypatch.setattr("cache.trend_repo.SessionLocal", factory)
    return factory


@patch("cache.trend_repo.trend_api.fetch")
def test_cache_miss_fetches_and_stores(mock_fetch, session_factory) -> None:
    mock_fetch.return_value = _TREND_RESULT

    result = get_trend("아이스아메리카노")

    mock_fetch.assert_called_once_with("아이스아메리카노")
    assert result == _TREND_RESULT

    with session_factory() as session:
        row = session.query(TrendCache).one()
        assert row.keyword == "아이스아메리카노"
        assert json.loads(row.result_json) == _TREND_RESULT


@patch("cache.trend_repo.trend_api.fetch")
def test_cache_hit_does_not_call_fetch(mock_fetch, session_factory) -> None:
    with session_factory() as session:
        session.add(
            TrendCache(keyword="아이스아메리카노", result_json=json.dumps(_TREND_RESULT))
        )
        session.commit()

    result = get_trend("아이스아메리카노")

    mock_fetch.assert_not_called()
    assert result == _TREND_RESULT


@patch("cache.trend_repo.trend_api.fetch")
def test_cache_expired_refetches(mock_fetch, session_factory) -> None:
    old_time = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=8)
    with session_factory() as session:
        session.add(
            TrendCache(
                keyword="아이스아메리카노",
                result_json=json.dumps(_TREND_RESULT),
                created_at=old_time,
            )
        )
        session.commit()
    mock_fetch.return_value = _TREND_RESULT

    result = get_trend("아이스아메리카노")

    mock_fetch.assert_called_once()
    assert result == _TREND_RESULT


@patch("cache.trend_repo.trend_api.fetch")
def test_fetch_failure_returns_none(mock_fetch, session_factory) -> None:
    mock_fetch.return_value = None

    result = get_trend("아이스아메리카노")

    assert result is None
    with session_factory() as session:
        assert session.query(TrendCache).count() == 0


@patch("cache.trend_repo.trend_api.fetch")
def test_keyword_variants_with_different_spacing_share_cache(mock_fetch, session_factory) -> None:
    """공백 유무만 다른 같은 의미의 검색어는 정규화돼 같은 캐시를 공유한다."""
    mock_fetch.return_value = _TREND_RESULT

    get_trend("아이스아메리카노")
    get_trend("아이스 아메리카노")

    mock_fetch.assert_called_once_with("아이스아메리카노")


@patch("cache.trend_repo.trend_api.fetch")
def test_fetch_called_with_normalized_keyword(mock_fetch, session_factory) -> None:
    mock_fetch.return_value = _TREND_RESULT

    get_trend("아이스 아메리카노")

    mock_fetch.assert_called_once_with("아이스아메리카노")


@patch("cache.trend_repo.trend_api.fetch")
def test_picks_latest_row_when_created_at_ties(mock_fetch, session_factory) -> None:
    """SQLite CURRENT_TIMESTAMP는 초 단위라 짧은 시간에 여러 번 적재되면 created_at이
    같을 수 있다 — 이때도 id 기준으로 가장 최신(나중에 적재된) 행을 골라야 한다."""
    same_time = datetime.now(UTC).replace(tzinfo=None)
    older_result = {**_TREND_RESULT, "direction": "하락"}
    newer_result = {**_TREND_RESULT, "direction": "상승"}
    with session_factory() as session:
        session.add(
            TrendCache(
                keyword="아이스아메리카노",
                result_json=json.dumps(older_result),
                created_at=same_time,
            )
        )
        session.add(
            TrendCache(
                keyword="아이스아메리카노",
                result_json=json.dumps(newer_result),
                created_at=same_time,
            )
        )
        session.commit()

    result = get_trend("아이스아메리카노")

    mock_fetch.assert_not_called()
    assert result["direction"] == "상승"


@patch("cache.trend_repo.trend_api.fetch")
def test_db_failure_falls_back_to_live_fetch_without_crashing(mock_fetch, monkeypatch) -> None:
    """캐시 DB 조회·적재가 모두 실패해도 예외를 삼키고 실시간 API 결과를 반환한다."""
    broken_factory = sessionmaker(bind=create_engine("sqlite:////nonexistent_dir_xyz/cache.db"))
    monkeypatch.setattr("cache.trend_repo.SessionLocal", broken_factory)
    mock_fetch.return_value = _TREND_RESULT

    result = get_trend("아이스아메리카노")

    assert result == _TREND_RESULT


@patch("cache.trend_repo.trend_api.fetch")
def test_corrupted_cache_json_falls_back_to_live_fetch(mock_fetch, session_factory) -> None:
    """저장된 result_json이 파싱 자체가 안 되면 예외 없이 캐시 미스로 처리한다."""
    with session_factory() as session:
        session.add(TrendCache(keyword="아이스아메리카노", result_json="not-json{"))
        session.commit()
    mock_fetch.return_value = _TREND_RESULT

    result = get_trend("아이스아메리카노")

    mock_fetch.assert_called_once()
    assert result == _TREND_RESULT


@pytest.mark.parametrize(
    "malformed_payload",
    [
        {"keyword": "아이스아메리카노", "direction": "알수없음", "related": []},  # direction 값 오류
        {"keyword": "아이스아메리카노", "direction": "상승", "related": "냉커피"},  # related가 리스트 아님
        {"keyword": "아이스아메리카노", "direction": "상승", "related": [1, 2]},  # related 항목이 문자열 아님
        {"keyword": 123, "direction": "상승", "related": []},  # keyword가 문자열 아님
        {"direction": "상승", "related": []},  # keyword 필드 자체 누락
        ["keyword", "direction"],
        "그냥 문자열",
    ],
)
@patch("cache.trend_repo.trend_api.fetch")
def test_cache_with_wrong_shape_falls_back_to_live_fetch(
    mock_fetch, session_factory, malformed_payload
) -> None:
    """JSON 파싱은 성공했지만 계약 형식이 아니면 미스로 처리한다."""
    with session_factory() as session:
        session.add(
            TrendCache(keyword="아이스아메리카노", result_json=json.dumps(malformed_payload))
        )
        session.commit()
    mock_fetch.return_value = _TREND_RESULT

    result = get_trend("아이스아메리카노")

    mock_fetch.assert_called_once()
    assert result == _TREND_RESULT


@patch("cache.trend_repo.trend_api.fetch")
def test_cache_hit_is_logged(mock_fetch, session_factory, caplog) -> None:
    with session_factory() as session:
        session.add(
            TrendCache(keyword="아이스아메리카노", result_json=json.dumps(_TREND_RESULT))
        )
        session.commit()

    with caplog.at_level(logging.INFO, logger="cache.trend_repo"):
        get_trend("아이스아메리카노")

    assert any(
        record.levelno == logging.INFO and "cache hit" in record.message
        for record in caplog.records
    )


@patch("cache.trend_repo.trend_api.fetch")
def test_cache_miss_is_logged(mock_fetch, session_factory, caplog) -> None:
    mock_fetch.return_value = _TREND_RESULT

    with caplog.at_level(logging.INFO, logger="cache.trend_repo"):
        get_trend("아이스아메리카노")

    assert any(
        record.levelno == logging.INFO and "cache miss" in record.message
        for record in caplog.records
    )


@patch("cache.trend_repo.trend_api.fetch")
def test_repeated_cache_miss_upserts_instead_of_inserting_new_row(
    mock_fetch, session_factory
) -> None:
    """같은 검색어로 반복 적재되면 새 행을 계속 추가하는 대신 기존 행을 갱신한다
    (market_repo가 D-053으로 이미 적용한 것과 동일 패턴) — trend_cache에는 UNIQUE
    인덱스가 없어 upsert로 미리 방어하지 않으면 같은 검색어가 조회될 때마다 행이
    쌓인다(PM 리뷰)."""
    mock_fetch.return_value = _TREND_RESULT
    get_trend("아이스아메리카노")
    with session_factory() as session:
        assert session.query(TrendCache).count() == 1

    with session_factory() as session:
        row = session.query(TrendCache).one()
        row.created_at = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=8)
        session.commit()

    other_result = {**_TREND_RESULT, "direction": "하락"}
    mock_fetch.return_value = other_result
    get_trend("아이스아메리카노")

    with session_factory() as session:
        assert session.query(TrendCache).count() == 1
        row = session.query(TrendCache).one()
        assert json.loads(row.result_json)["direction"] == "하락"


@patch("cache.trend_repo.trend_api.fetch")
def test_upsert_refreshes_ttl_even_when_payload_is_identical(mock_fetch, session_factory) -> None:
    """만료된 캐시를 재적재할 때 새로 받아온 값이 기존 값과 동일해도 created_at이
    갱신돼야 한다 — market_repo와 같은 이유로, 값이 안 바뀌면 SQLAlchemy가 UPDATE
    대상에서 제외해 갱신이 안 되면 다음 조회도 계속 만료로 판정된다."""
    old_time = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=8)
    with session_factory() as session:
        session.add(
            TrendCache(
                keyword="아이스아메리카노",
                result_json=json.dumps(_TREND_RESULT),
                created_at=old_time,
            )
        )
        session.commit()
    mock_fetch.return_value = _TREND_RESULT  # 기존 캐시와 동일한 payload

    get_trend("아이스아메리카노")

    with session_factory() as session:
        row = session.query(TrendCache).one()
        assert row.created_at > old_time + timedelta(days=7)


@patch("cache.trend_repo.trend_api.fetch")
def test_db_read_failure_logs_warning(mock_fetch, monkeypatch, caplog) -> None:
    broken_factory = sessionmaker(bind=create_engine("sqlite:////nonexistent_dir_xyz/cache.db"))
    monkeypatch.setattr("cache.trend_repo.SessionLocal", broken_factory)
    mock_fetch.return_value = _TREND_RESULT

    with caplog.at_level(logging.WARNING, logger="cache.trend_repo"):
        get_trend("아이스아메리카노")

    assert any(
        record.levelno == logging.WARNING and "cache read failed" in record.message
        for record in caplog.records
    )
    # API 키·응답 원문이 로그에 남지 않아야 한다
    logged_text = " ".join(record.message for record in caplog.records)
    assert "NAVER_CLIENT_SECRET" not in logged_text
    assert "NAVER_AD_SECRET_KEY" not in logged_text
