# market_api 클라이언트 테스트
from unittest.mock import MagicMock, patch

import pytest

from model_consult.clients.market_api import _haversine_m, aggregate, fetch

_GANGNAM_LAT, _GANGNAM_LNG = 37.4980, 127.0276

_STORES = [
    {
        "indsLclsNm": "음식점",
        "indsMclsNm": "카페",
        "indsSclsNm": "커피전문점",
        "lat": 37.4981,
        "lon": 127.0277,
    },
    {
        "indsLclsNm": "음식점",
        "indsMclsNm": "카페",
        "indsSclsNm": "커피전문점",
        "lat": 37.5100,
        "lon": 127.0400,
    },
    {
        "indsLclsNm": "소매업",
        "indsMclsNm": "편의점",
        "indsSclsNm": "편의점",
        "lat": 37.4982,
        "lon": 127.0278,
    },
]


def test_aggregate_without_industry_leaves_same_industry_fields_unknown() -> None:
    result = aggregate(_STORES, total_count=3, industry=None, lat=_GANGNAM_LAT, lng=_GANGNAM_LNG)

    assert result["total_count"] == 3
    assert result["same_industry_count"] is None
    assert result["nearest_distance_m"] is None
    assert result["industry_breakdown"] == {"카페": 2, "편의점": 1}


def test_aggregate_with_industry_counts_matches_and_nearest_distance() -> None:
    result = aggregate(_STORES, total_count=3, industry="카페", lat=_GANGNAM_LAT, lng=_GANGNAM_LNG)

    assert result["total_count"] == 3
    assert result["same_industry_count"] == 2
    # 두 카페 중 더 가까운 쪽(약 14m)이 선택돼야 한다 — 느슨한 상한만 두면 0이나 1을 반환해도
    # 통과하므로, 실제 예상 거리 근방으로 좁게 검증한다.
    assert result["nearest_distance_m"] == pytest.approx(14, abs=3)


def test_haversine_matches_known_distance_for_one_degree_latitude() -> None:
    """위도 1도 차이는 지구 어디서나(자오선 기준) 약 111.32km여야 한다."""
    distance = _haversine_m(0.0, 0.0, 1.0, 0.0)

    assert distance == pytest.approx(111_320, rel=0.01)


def test_aggregate_with_industry_no_match_returns_zero_and_none_distance() -> None:
    result = aggregate(_STORES, total_count=3, industry="병원", lat=_GANGNAM_LAT, lng=_GANGNAM_LNG)

    assert result["same_industry_count"] == 0
    assert result["nearest_distance_m"] is None


def test_aggregate_ignores_store_with_non_string_industry_name() -> None:
    """indsMclsNm이 문자열이 아니면(예: 손상된 캐시) 집계에서 조용히 제외한다."""
    stores = [*_STORES, {"indsLclsNm": "음식점", "indsMclsNm": ["카페"], "lat": 37.5, "lon": 127.0}]

    result = aggregate(stores, total_count=4, industry=None, lat=_GANGNAM_LAT, lng=_GANGNAM_LNG)

    assert result["industry_breakdown"] == {"카페": 2, "편의점": 1}


def test_aggregate_ignores_store_with_non_numeric_coordinates() -> None:
    """lat/lon이 숫자가 아니거나 bool이면(예: 손상된 캐시) 거리 계산에서 제외한다."""
    stores = [
        {
            "indsLclsNm": "음식점",
            "indsMclsNm": "카페",
            "indsSclsNm": "커피전문점",
            "lat": "37.4981",
            "lon": 127.0277,
        },
        {
            "indsLclsNm": "음식점",
            "indsMclsNm": "카페",
            "indsSclsNm": "커피전문점",
            "lat": True,
            "lon": 127.0277,
        },
    ]

    result = aggregate(stores, total_count=2, industry="카페", lat=_GANGNAM_LAT, lng=_GANGNAM_LNG)

    assert result["same_industry_count"] == 2
    assert result["nearest_distance_m"] is None


def test_aggregate_ignores_coordinate_beyond_float_range() -> None:
    """float() 표현 범위를 넘는 거대한 정수 좌표도 OverflowError 없이 제외한다."""
    huge_int = 10**10000
    stores = [
        {
            "indsLclsNm": "음식점",
            "indsMclsNm": "카페",
            "indsSclsNm": "커피전문점",
            "lat": huge_int,
            "lon": 127.0277,
        }
    ]

    result = aggregate(stores, total_count=1, industry="카페", lat=_GANGNAM_LAT, lng=_GANGNAM_LNG)

    assert result["same_industry_count"] == 1
    assert result["nearest_distance_m"] is None


def test_aggregate_ignores_non_dict_items_in_stores() -> None:
    """stores 안에 dict가 아닌 요소가 섞여 있어도(예: 예상 밖 API 응답) 예외 없이 제외한다."""
    stores = [*_STORES, None, "문자열", 123]

    result = aggregate(stores, total_count=6, industry="카페", lat=_GANGNAM_LAT, lng=_GANGNAM_LNG)

    assert result["same_industry_count"] == 2
    assert result["industry_breakdown"] == {"카페": 2, "편의점": 1}


@patch("model_consult.clients.market_api.httpx.get")
def test_fetch_builds_request_and_returns_none_without_api_key(
    mock_get: MagicMock, monkeypatch
) -> None:
    monkeypatch.delenv("MARKET_API_KEY", raising=False)

    result = fetch(_GANGNAM_LAT, _GANGNAM_LNG, radius=500, industry="카페")

    assert result is None
    mock_get.assert_not_called()


@patch("model_consult.clients.market_api.httpx.get")
def test_fetch_parses_response_into_contract_shape(mock_get: MagicMock, monkeypatch) -> None:
    monkeypatch.setenv("MARKET_API_KEY", "test-decoding-key")
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "header": {"resultCode": "00", "resultMsg": "NORMAL SERVICE"},
        "body": {
            "items": _STORES,
            "numOfRows": 3,
            "pageNo": 1,
            "totalCount": 3,
        },
    }
    mock_get.return_value = mock_response

    result = fetch(_GANGNAM_LAT, _GANGNAM_LNG, radius=500, industry="카페")

    assert result["total_count"] == 3
    assert result["same_industry_count"] == 2

    called_params = mock_get.call_args.kwargs["params"]
    assert called_params["serviceKey"] == "test-decoding-key"
    assert called_params["radius"] == 500
    assert called_params["cx"] == _GANGNAM_LNG
    assert called_params["cy"] == _GANGNAM_LAT


@patch("model_consult.clients.market_api.httpx.get")
def test_fetch_ignores_non_dict_items_from_live_response(mock_get: MagicMock, monkeypatch) -> None:
    """실시간 API가 items 안에 예상 밖 값(null 등)을 섞어 보내도 예외 없이 제외한다."""
    monkeypatch.setenv("MARKET_API_KEY", "test-decoding-key")
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "header": {"resultCode": "00", "resultMsg": "NORMAL SERVICE"},
        "body": {"items": [*_STORES, None], "numOfRows": 4, "pageNo": 1, "totalCount": 4},
    }
    mock_get.return_value = mock_response

    result = fetch(_GANGNAM_LAT, _GANGNAM_LNG, radius=500, industry="카페")

    assert result["same_industry_count"] == 2


@patch("model_consult.clients.market_api.httpx.get")
def test_fetch_returns_none_when_api_reports_error_via_result_code(
    mock_get: MagicMock, monkeypatch
) -> None:
    """HTTP 200이어도 header.resultCode가 00이 아니면(예: 인증키 오류) 정상 데이터로 취급하지 않는다."""
    monkeypatch.setenv("MARKET_API_KEY", "wrong-key")
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "header": {"resultCode": "30", "resultMsg": "SERVICE_KEY_IS_NOT_REGISTERED_ERROR"},
        "body": {},
    }
    mock_get.return_value = mock_response

    result = fetch(_GANGNAM_LAT, _GANGNAM_LNG, radius=500, industry="카페")

    assert result is None


@patch("model_consult.clients.market_api.httpx.get")
def test_fetch_returns_none_when_response_is_not_json(mock_get: MagicMock, monkeypatch) -> None:
    """HTTP 200이어도 본문이 JSON이 아니면(XML/텍스트 오류 응답 등) None을 반환한다."""
    monkeypatch.setenv("MARKET_API_KEY", "test-decoding-key")
    mock_response = MagicMock()
    mock_response.json.side_effect = ValueError("not json")
    mock_get.return_value = mock_response

    result = fetch(_GANGNAM_LAT, _GANGNAM_LNG, radius=500, industry="카페")

    assert result is None
