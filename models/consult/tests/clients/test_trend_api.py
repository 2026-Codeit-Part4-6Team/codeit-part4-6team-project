# trend_api 클라이언트 테스트
from datetime import date
from unittest.mock import MagicMock, patch

from models.consult.clients.trend_api import _direction_from_series, fetch, fetch_raw


def _series(*ratios: float) -> list[dict]:
    return [{"period": f"2026-08-{i + 1:02d}", "ratio": ratio} for i, ratio in enumerate(ratios)]


def test_direction_rises_when_second_half_average_is_higher() -> None:
    assert _direction_from_series(_series(10, 10, 10, 50, 50, 50)) == "상승"


def test_direction_falls_when_second_half_average_is_lower() -> None:
    assert _direction_from_series(_series(50, 50, 50, 10, 10, 10)) == "하락"


def test_direction_stays_when_change_is_within_threshold() -> None:
    assert _direction_from_series(_series(50, 51, 49, 50, 50, 50)) == "유지"


def test_direction_rises_at_exact_threshold() -> None:
    """변화율이 정확히 +10%(경계값 포함)이면 유지가 아니라 상승으로 판단한다."""
    assert _direction_from_series(_series(100, 100, 100, 110, 110, 110)) == "상승"


def test_direction_falls_at_exact_threshold() -> None:
    """변화율이 정확히 -10%(경계값 포함)이면 유지가 아니라 하락으로 판단한다."""
    assert _direction_from_series(_series(100, 100, 100, 90, 90, 90)) == "하락"


def test_direction_rises_at_exact_threshold_with_float_ratios() -> None:
    """3 → 3.3처럼 부동소수점 오차로 change_ratio가 0.1이 아니라
    0.09999999999999994로 계산되는 경우에도 경계값으로 인정해 상승으로 판단한다."""
    assert _direction_from_series(_series(3, 3, 3, 3.3, 3.3, 3.3)) == "상승"


def test_direction_falls_at_exact_threshold_with_float_ratios() -> None:
    assert _direction_from_series(_series(3, 3, 3, 2.7, 2.7, 2.7)) == "하락"


def test_direction_stays_when_fewer_than_two_points() -> None:
    assert _direction_from_series(_series(50)) == "유지"
    assert _direction_from_series([]) == "유지"


def test_direction_ignores_non_dict_or_non_numeric_points() -> None:
    """실시간 API가 예상 밖 값(null 등)을 섞어 보내도 예외 없이 걸러낸다."""
    data = [*_series(10, 10, 10), None, {"period": "x"}, "문자열", *_series(50, 50, 50)]

    assert _direction_from_series(data) == "상승"


def test_direction_handles_zero_first_half_average() -> None:
    """0으로 나누는 예외 없이, 0에서 상승했으면 상승으로 판단한다."""
    assert _direction_from_series(_series(0, 0, 10, 10)) == "상승"
    assert _direction_from_series(_series(0, 0, 0, 0)) == "유지"


@patch("models.consult.clients.trend_api.httpx.post")
def test_fetch_returns_none_without_credentials(mock_post: MagicMock, monkeypatch) -> None:
    monkeypatch.delenv("NAVER_CLIENT_ID", raising=False)
    monkeypatch.delenv("NAVER_CLIENT_SECRET", raising=False)

    result = fetch("아이스아메리카노")

    assert result is None
    mock_post.assert_not_called()


@patch("models.consult.clients.trend_api.httpx.post")
def test_fetch_raw_requests_exactly_lookback_days_range(mock_post: MagicMock, monkeypatch) -> None:
    """시작일·종료일 모두 포함해 정확히 _LOOKBACK_DAYS(30)일 구간을 요청한다(양끝 포함이라 날짜 차이는 29)."""
    monkeypatch.setenv("NAVER_CLIENT_ID", "test-id")
    monkeypatch.setenv("NAVER_CLIENT_SECRET", "test-secret")
    mock_response = MagicMock()
    mock_response.json.return_value = {"results": []}
    mock_post.return_value = mock_response

    fetch_raw("아이스아메리카노")

    called_body = mock_post.call_args.kwargs["json"]
    start = date.fromisoformat(called_body["startDate"])
    end = date.fromisoformat(called_body["endDate"])
    assert (end - start).days == 29


@patch("models.consult.clients.trend_api.search_ad_api.fetch_related_keywords")
@patch("models.consult.clients.trend_api.httpx.post")
def test_fetch_parses_response_into_contract_shape(
    mock_post: MagicMock, mock_fetch_related: MagicMock, monkeypatch
) -> None:
    monkeypatch.setenv("NAVER_CLIENT_ID", "test-id")
    monkeypatch.setenv("NAVER_CLIENT_SECRET", "test-secret")
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "startDate": "2026-07-15",
        "endDate": "2026-08-13",
        "timeUnit": "date",
        "results": [
            {
                "title": "아이스아메리카노",
                "keywords": ["아이스아메리카노"],
                "data": _series(10, 10, 10, 50, 50, 50),
            }
        ],
    }
    mock_post.return_value = mock_response
    mock_fetch_related.return_value = ["냉커피", "여름음료"]

    result = fetch("아이스아메리카노")

    assert result == {
        "keyword": "아이스아메리카노",
        "direction": "상승",
        "related": ["냉커피", "여름음료"],
        "weather": None,
    }
    mock_fetch_related.assert_called_once_with("아이스아메리카노")

    called_headers = mock_post.call_args.kwargs["headers"]
    assert called_headers["X-NCP-APIGW-API-KEY-ID"] == "test-id"
    assert called_headers["X-NCP-APIGW-API-KEY"] == "test-secret"
    called_body = mock_post.call_args.kwargs["json"]
    assert called_body["keywordGroups"] == [
        {"groupName": "아이스아메리카노", "keywords": ["아이스아메리카노"]}
    ]


@patch("models.consult.clients.trend_api.search_ad_api.fetch_related_keywords")
@patch("models.consult.clients.trend_api.httpx.post")
def test_fetch_keeps_trend_result_when_related_keywords_fail(
    mock_post: MagicMock, mock_fetch_related: MagicMock, monkeypatch
) -> None:
    """search_ad_api가 실패해도(자격증명 없음 등) 트렌드 조회 자체는 계속된다 — 부분 성공 허용.

    계약(docs/repo_contract.md)상 related는 항상 list[str]이어야 하므로(weather와
    달리 None 불허), search_ad_api의 실패(None)는 여기서 빈 리스트로 정규화된다.
    """
    monkeypatch.setenv("NAVER_CLIENT_ID", "test-id")
    monkeypatch.setenv("NAVER_CLIENT_SECRET", "test-secret")
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "results": [{"data": _series(10, 10, 10, 50, 50, 50)}],
    }
    mock_post.return_value = mock_response
    mock_fetch_related.return_value = None

    result = fetch("아이스아메리카노")

    assert result["direction"] == "상승"
    assert result["related"] == []


@patch("models.consult.clients.trend_api.httpx.post")
def test_fetch_returns_none_when_results_missing_or_empty(mock_post: MagicMock, monkeypatch) -> None:
    monkeypatch.setenv("NAVER_CLIENT_ID", "test-id")
    monkeypatch.setenv("NAVER_CLIENT_SECRET", "test-secret")
    mock_response = MagicMock()
    mock_response.json.return_value = {"results": []}
    mock_post.return_value = mock_response

    result = fetch("아이스아메리카노")

    assert result is None


@patch("models.consult.clients.trend_api.httpx.post")
def test_fetch_returns_none_when_response_is_not_json(mock_post: MagicMock, monkeypatch) -> None:
    """HTTP 200이어도 본문이 JSON이 아니면(오류 응답 등) None을 반환한다."""
    monkeypatch.setenv("NAVER_CLIENT_ID", "test-id")
    monkeypatch.setenv("NAVER_CLIENT_SECRET", "test-secret")
    mock_response = MagicMock()
    mock_response.json.side_effect = ValueError("not json")
    mock_post.return_value = mock_response

    result = fetch("아이스아메리카노")

    assert result is None


@patch("models.consult.clients.trend_api.httpx.post")
def test_fetch_returns_none_when_http_error_raised(mock_post: MagicMock, monkeypatch) -> None:
    monkeypatch.setenv("NAVER_CLIENT_ID", "test-id")
    monkeypatch.setenv("NAVER_CLIENT_SECRET", "test-secret")
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = httpx_error()
    mock_post.return_value = mock_response

    result = fetch("아이스아메리카노")

    assert result is None


def httpx_error():
    import httpx as _httpx

    request = _httpx.Request("POST", "https://naverapihub.apigw.ntruss.com/search-trend/v1/search")
    response = _httpx.Response(status_code=401, request=request)
    return _httpx.HTTPStatusError("unauthorized", request=request, response=response)
