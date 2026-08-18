# market_api 클라이언트 테스트
from unittest.mock import MagicMock, patch

import pytest

from models.consult.clients.market_api import (
    _haversine_m,
    aggregate,
    fetch,
    fetch_by_code,
    industry_code_for,
)

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
    {
        "indsLclsNm": "의료",
        "indsMclsNm": "병원",
        "indsSclsNm": "일반병원",
        "lat": 37.4983,
        "lon": 127.0279,
    },
]


def test_aggregate_without_industry_leaves_same_industry_fields_unknown() -> None:
    result = aggregate(_STORES, total_count=3, industry=None, lat=_GANGNAM_LAT, lng=_GANGNAM_LNG)

    assert result["total_count"] == 3
    assert result["same_industry_count"] is None
    assert result["nearest_distance_m"] is None
    assert result["industry_breakdown"] == {"카페": 2, "편의점": 1, "병원": 1}


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
    result = aggregate(_STORES, total_count=3, industry="미용실", lat=_GANGNAM_LAT, lng=_GANGNAM_LNG)

    assert result["same_industry_count"] == 0
    assert result["nearest_distance_m"] is None


def test_aggregate_ignores_store_with_non_string_industry_name() -> None:
    """indsMclsNm이 문자열이 아니면(예: 손상된 캐시) 집계에서 조용히 제외한다."""
    stores = [*_STORES, {"indsLclsNm": "음식점", "indsMclsNm": ["카페"], "lat": 37.5, "lon": 127.0}]

    result = aggregate(stores, total_count=4, industry=None, lat=_GANGNAM_LAT, lng=_GANGNAM_LNG)

    assert result["industry_breakdown"] == {"카페": 2, "편의점": 1, "병원": 1}


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
    assert result["industry_breakdown"] == {"카페": 2, "편의점": 1, "병원": 1}


def test_load_industry_code_map_returns_empty_when_file_missing(monkeypatch, tmp_path) -> None:
    """매핑 파일이 없으면 예외 없이 빈 매핑을 반환한다 — 모든 industry가 텍스트
    매칭으로 폴백한다(D-041)."""
    from models.consult.clients import market_api

    monkeypatch.setattr(market_api, "_INDUSTRY_CODE_MAP_PATH", tmp_path / "nonexistent.json")

    assert market_api._load_industry_code_map() == {}


def test_load_industry_code_map_returns_empty_when_json_is_corrupted(monkeypatch, tmp_path) -> None:
    from models.consult.clients import market_api

    bad_file = tmp_path / "corrupted.json"
    bad_file.write_text("not-json{", encoding="utf-8")
    monkeypatch.setattr(market_api, "_INDUSTRY_CODE_MAP_PATH", bad_file)

    assert market_api._load_industry_code_map() == {}


def test_load_industry_code_map_returns_empty_when_top_level_is_not_an_object(
    monkeypatch, tmp_path
) -> None:
    from models.consult.clients import market_api

    array_file = tmp_path / "array.json"
    array_file.write_text('["카페", "I21201"]', encoding="utf-8")
    monkeypatch.setattr(market_api, "_INDUSTRY_CODE_MAP_PATH", array_file)

    assert market_api._load_industry_code_map() == {}


def test_industry_code_for_known_industry_returns_code() -> None:
    """D-043 단일 소스(shared_data/industry_code_map.json)에 있는 업종은 코드를 반환한다."""
    assert industry_code_for("카페") == "I21201"


def test_industry_code_for_unknown_industry_returns_none() -> None:
    assert industry_code_for("존재하지않는업종") is None


def test_aggregate_uses_matched_stores_when_given_instead_of_text_matching() -> None:
    """matched_stores/matched_total_count가 주어지면(D-041/D-042 업종코드 필터 호출 결과)
    텍스트 매칭 대신 그 값을 그대로 쓴다 — 더 정확하기 때문이다."""
    matched_stores = [{"lat": 37.4981, "lon": 127.0277}]

    result = aggregate(
        _STORES,
        total_count=3,
        industry="카페",
        lat=_GANGNAM_LAT,
        lng=_GANGNAM_LNG,
        matched_stores=matched_stores,
        matched_total_count=177,
    )

    assert result["total_count"] == 3
    assert result["same_industry_count"] == 177
    assert result["nearest_distance_m"] == pytest.approx(14, abs=3)


@patch("models.consult.clients.market_api.httpx.get")
def test_fetch_by_code_includes_inds_scls_cd_param(mock_get: MagicMock, monkeypatch) -> None:
    monkeypatch.setenv("MARKET_API_KEY", "test-decoding-key")
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "header": {"resultCode": "00", "resultMsg": "NORMAL SERVICE"},
        "body": {"items": _STORES[:1], "totalCount": 177},
    }
    mock_get.return_value = mock_response

    result = fetch_by_code(_GANGNAM_LAT, _GANGNAM_LNG, 500, "I21201")

    assert result == (_STORES[:1], 177)
    called_params = mock_get.call_args.kwargs["params"]
    assert called_params["indsSclsCd"] == "I21201"


@patch("models.consult.clients.market_api.httpx.get")
def test_fetch_calls_code_filter_when_industry_has_mapping(mock_get: MagicMock, monkeypatch) -> None:
    """카페처럼 코드 매핑이 있는 industry는 API를 2번(전체 조회 + 코드 필터 조회) 호출하고,
    same_industry_count는 코드 필터 호출의 totalCount를 그대로 쓴다(텍스트 매칭 결과가 아님)."""
    monkeypatch.setenv("MARKET_API_KEY", "test-decoding-key")
    raw_response = MagicMock()
    raw_response.json.return_value = {
        "header": {"resultCode": "00", "resultMsg": "NORMAL SERVICE"},
        "body": {"items": _STORES, "totalCount": 6691},
    }
    filtered_response = MagicMock()
    filtered_response.json.return_value = {
        "header": {"resultCode": "00", "resultMsg": "NORMAL SERVICE"},
        "body": {"items": _STORES[:1], "totalCount": 177},
    }
    mock_get.side_effect = [raw_response, filtered_response]

    result = fetch(_GANGNAM_LAT, _GANGNAM_LNG, radius=500, industry="카페")

    assert mock_get.call_count == 2
    assert result["total_count"] == 6691
    assert result["same_industry_count"] == 177
    second_call_params = mock_get.call_args_list[1].kwargs["params"]
    assert second_call_params["indsSclsCd"] == "I21201"


@patch("models.consult.clients.market_api.httpx.get")
def test_fetch_falls_back_to_text_matching_when_industry_has_no_code_mapping(
    mock_get: MagicMock, monkeypatch
) -> None:
    """코드 매핑이 없는 industry는 기존처럼 텍스트 매칭만 하고 API는 1번만 호출한다(D-041 폴백)."""
    monkeypatch.setenv("MARKET_API_KEY", "test-decoding-key")
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "header": {"resultCode": "00", "resultMsg": "NORMAL SERVICE"},
        "body": {"items": _STORES, "totalCount": 4},
    }
    mock_get.return_value = mock_response

    result = fetch(_GANGNAM_LAT, _GANGNAM_LNG, radius=500, industry="병원")

    assert mock_get.call_count == 1
    assert result["same_industry_count"] == 1


@patch("models.consult.clients.market_api.httpx.get")
def test_fetch_falls_back_to_text_matching_when_code_filter_call_fails(
    mock_get: MagicMock, monkeypatch
) -> None:
    """코드 매핑은 있지만 2번째(필터) 호출이 실패하면 결과 자체를 버리지 않고
    텍스트 매칭으로 폴백한다(D-041)."""
    monkeypatch.setenv("MARKET_API_KEY", "test-decoding-key")
    raw_response = MagicMock()
    raw_response.json.return_value = {
        "header": {"resultCode": "00", "resultMsg": "NORMAL SERVICE"},
        "body": {"items": _STORES, "totalCount": 3},
    }
    failed_response = MagicMock()
    failed_response.json.side_effect = ValueError("not json")
    mock_get.side_effect = [raw_response, failed_response]

    result = fetch(_GANGNAM_LAT, _GANGNAM_LNG, radius=500, industry="카페")

    assert result is not None
    assert result["same_industry_count"] == 2


@patch("models.consult.clients.market_api.httpx.get")
def test_fetch_builds_request_and_returns_none_without_api_key(
    mock_get: MagicMock, monkeypatch
) -> None:
    monkeypatch.delenv("MARKET_API_KEY", raising=False)

    result = fetch(_GANGNAM_LAT, _GANGNAM_LNG, radius=500, industry="카페")

    assert result is None
    mock_get.assert_not_called()


@patch("models.consult.clients.market_api.httpx.get")
def test_fetch_parses_response_into_contract_shape(mock_get: MagicMock, monkeypatch) -> None:
    """industry_code_for() 매핑이 없는 업종(병원)을 써서 원본 파싱·텍스트 매칭 경로만
    검증한다 — 업종코드 필터 2회 호출 경로는 test_fetch_calls_code_filter_when_industry_has_mapping에서
    따로 검증한다."""
    monkeypatch.setenv("MARKET_API_KEY", "test-decoding-key")
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "header": {"resultCode": "00", "resultMsg": "NORMAL SERVICE"},
        "body": {
            "items": _STORES,
            "numOfRows": 4,
            "pageNo": 1,
            "totalCount": 4,
        },
    }
    mock_get.return_value = mock_response

    result = fetch(_GANGNAM_LAT, _GANGNAM_LNG, radius=500, industry="병원")

    assert result["total_count"] == 4
    assert result["same_industry_count"] == 1

    called_params = mock_get.call_args.kwargs["params"]
    assert called_params["serviceKey"] == "test-decoding-key"
    assert called_params["radius"] == 500
    assert called_params["cx"] == _GANGNAM_LNG
    assert called_params["cy"] == _GANGNAM_LAT


@patch("models.consult.clients.market_api.httpx.get")
def test_fetch_ignores_non_dict_items_from_live_response(mock_get: MagicMock, monkeypatch) -> None:
    """실시간 API가 items 안에 예상 밖 값(null 등)을 섞어 보내도 예외 없이 제외한다."""
    monkeypatch.setenv("MARKET_API_KEY", "test-decoding-key")
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "header": {"resultCode": "00", "resultMsg": "NORMAL SERVICE"},
        "body": {"items": [*_STORES, None], "numOfRows": 5, "pageNo": 1, "totalCount": 5},
    }
    mock_get.return_value = mock_response

    result = fetch(_GANGNAM_LAT, _GANGNAM_LNG, radius=500, industry="병원")

    assert result["same_industry_count"] == 1


@patch("models.consult.clients.market_api.httpx.get")
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


@patch("models.consult.clients.market_api.httpx.get")
def test_fetch_returns_none_when_response_is_valid_json_but_not_an_object(
    mock_get: MagicMock, monkeypatch
) -> None:
    """HTTP 200 + 유효한 JSON이어도 최상위가 dict가 아니면(예: 배열) 예외 없이 None을 반환한다."""
    monkeypatch.setenv("MARKET_API_KEY", "test-decoding-key")
    mock_response = MagicMock()
    mock_response.json.return_value = []
    mock_get.return_value = mock_response

    result = fetch(_GANGNAM_LAT, _GANGNAM_LNG, radius=500, industry="카페")

    assert result is None


@patch("models.consult.clients.market_api.httpx.get")
def test_fetch_returns_none_when_body_is_not_an_object(mock_get: MagicMock, monkeypatch) -> None:
    """header는 정상이어도 body가 dict가 아니면(예상 밖 응답 형태) 예외 없이 None을 반환한다."""
    monkeypatch.setenv("MARKET_API_KEY", "test-decoding-key")
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "header": {"resultCode": "00", "resultMsg": "NORMAL SERVICE"},
        "body": "예상 밖 문자열",
    }
    mock_get.return_value = mock_response

    result = fetch(_GANGNAM_LAT, _GANGNAM_LNG, radius=500, industry="카페")

    assert result is None


@patch("models.consult.clients.market_api.httpx.get")
def test_fetch_returns_none_when_item_is_not_list_or_dict(mock_get: MagicMock, monkeypatch) -> None:
    """items.item이 리스트도 dict도 아니면(예상 밖 응답 형태) 예외 없이 None을 반환한다."""
    monkeypatch.setenv("MARKET_API_KEY", "test-decoding-key")
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "header": {"resultCode": "00", "resultMsg": "NORMAL SERVICE"},
        "body": {"items": {"item": 123}, "totalCount": 1},
    }
    mock_get.return_value = mock_response

    result = fetch(_GANGNAM_LAT, _GANGNAM_LNG, radius=500, industry="카페")

    assert result is None


@patch("models.consult.clients.market_api.httpx.get")
def test_fetch_returns_none_when_header_is_not_an_object(mock_get: MagicMock, monkeypatch) -> None:
    """header가 dict가 아니면(예상 밖 응답 형태) 예외 없이 None을 반환한다."""
    monkeypatch.setenv("MARKET_API_KEY", "test-decoding-key")
    mock_response = MagicMock()
    mock_response.json.return_value = {"header": "예상 밖 문자열", "body": {}}
    mock_get.return_value = mock_response

    result = fetch(_GANGNAM_LAT, _GANGNAM_LNG, radius=500, industry="카페")

    assert result is None


@patch("models.consult.clients.market_api.httpx.get")
def test_fetch_returns_none_when_total_count_is_not_convertible_to_int(
    mock_get: MagicMock, monkeypatch
) -> None:
    """totalCount가 숫자로 변환할 수 없는 값이면 예외 없이 None을 반환한다."""
    monkeypatch.setenv("MARKET_API_KEY", "test-decoding-key")
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "header": {"resultCode": "00", "resultMsg": "NORMAL SERVICE"},
        "body": {"items": _STORES, "totalCount": "not-int"},
    }
    mock_get.return_value = mock_response

    result = fetch(_GANGNAM_LAT, _GANGNAM_LNG, radius=500, industry="카페")

    assert result is None


@patch("models.consult.clients.market_api.httpx.get")
def test_fetch_returns_none_when_response_is_not_json(mock_get: MagicMock, monkeypatch) -> None:
    """HTTP 200이어도 본문이 JSON이 아니면(XML/텍스트 오류 응답 등) None을 반환한다."""
    monkeypatch.setenv("MARKET_API_KEY", "test-decoding-key")
    mock_response = MagicMock()
    mock_response.json.side_effect = ValueError("not json")
    mock_get.return_value = mock_response

    result = fetch(_GANGNAM_LAT, _GANGNAM_LNG, radius=500, industry="카페")

    assert result is None
