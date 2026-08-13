# search_ad_api 클라이언트 테스트
from unittest.mock import MagicMock, patch

from models.consult.clients.search_ad_api import fetch_related_keywords


def _set_credentials(monkeypatch) -> None:
    monkeypatch.setenv("NAVER_AD_API_KEY", "test-api-key")
    monkeypatch.setenv("NAVER_AD_SECRET_KEY", "test-secret-key")
    monkeypatch.setenv("NAVER_AD_CUSTOMER_ID", "1234567")


@patch("models.consult.clients.search_ad_api.httpx.get")
def test_returns_none_without_credentials(mock_get: MagicMock, monkeypatch) -> None:
    monkeypatch.delenv("NAVER_AD_API_KEY", raising=False)
    monkeypatch.delenv("NAVER_AD_SECRET_KEY", raising=False)
    monkeypatch.delenv("NAVER_AD_CUSTOMER_ID", raising=False)

    result = fetch_related_keywords("아이스아메리카노")

    assert result is None
    mock_get.assert_not_called()


@patch("models.consult.clients.search_ad_api.httpx.get")
def test_fetch_parses_related_keywords(mock_get: MagicMock, monkeypatch) -> None:
    _set_credentials(monkeypatch)
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "keywordList": [
            {"relKeyword": "냉커피", "monthlyPcQcCnt": 1000},
            {"relKeyword": "여름음료", "monthlyPcQcCnt": 500},
        ]
    }
    mock_get.return_value = mock_response

    result = fetch_related_keywords("아이스아메리카노")

    assert result == ["냉커피", "여름음료"]

    called_headers = mock_get.call_args.kwargs["headers"]
    assert called_headers["X-API-KEY"] == "test-api-key"
    assert called_headers["X-Customer"] == "1234567"
    assert "X-Signature" in called_headers
    assert "X-Timestamp" in called_headers
    called_params = mock_get.call_args.kwargs["params"]
    assert called_params["hintKeywords"] == "아이스아메리카노"


@patch("models.consult.clients.search_ad_api.httpx.get")
def test_fetch_strips_whitespace_from_request_keyword(mock_get: MagicMock, monkeypatch) -> None:
    """공백 포함 키워드는 API가 Invalid Parameter로 거부하는 사례가 있어 공백을 제거해 요청한다."""
    _set_credentials(monkeypatch)
    mock_response = MagicMock()
    mock_response.json.return_value = {"keywordList": []}
    mock_get.return_value = mock_response

    fetch_related_keywords("아이스 아메리카노")

    called_params = mock_get.call_args.kwargs["params"]
    assert called_params["hintKeywords"] == "아이스아메리카노"


@patch("models.consult.clients.search_ad_api.httpx.get")
def test_fetch_excludes_input_keyword_with_different_spacing(mock_get: MagicMock, monkeypatch) -> None:
    """입력에 공백이 있고 응답 relKeyword는 공백 없이 와도 같은 키워드로 인식해 제외한다."""
    _set_credentials(monkeypatch)
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "keywordList": [
            {"relKeyword": "아이스아메리카노"},  # 공백 없이 온 입력 키워드 자체 — 제외
            {"relKeyword": "냉 커피"},  # 공백 포함 연관어 — 공백 제거해서 저장
        ]
    }
    mock_get.return_value = mock_response

    result = fetch_related_keywords("아이스 아메리카노")

    assert result == ["냉커피"]


@patch("models.consult.clients.search_ad_api.httpx.get")
def test_fetch_excludes_input_keyword_and_duplicates(mock_get: MagicMock, monkeypatch) -> None:
    _set_credentials(monkeypatch)
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "keywordList": [
            {"relKeyword": "아이스아메리카노"},  # 입력 키워드 자체 — 제외
            {"relKeyword": "냉커피"},
            {"relKeyword": "냉커피"},  # 중복 — 제외
        ]
    }
    mock_get.return_value = mock_response

    result = fetch_related_keywords("아이스아메리카노")

    assert result == ["냉커피"]


@patch("models.consult.clients.search_ad_api.httpx.get")
def test_fetch_caps_at_max_related_keywords(mock_get: MagicMock, monkeypatch) -> None:
    _set_credentials(monkeypatch)
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "keywordList": [{"relKeyword": f"연관어{i}"} for i in range(10)]
    }
    mock_get.return_value = mock_response

    result = fetch_related_keywords("아이스아메리카노")

    assert len(result) == 5


@patch("models.consult.clients.search_ad_api.httpx.get")
def test_fetch_ignores_non_dict_or_blank_items(mock_get: MagicMock, monkeypatch) -> None:
    _set_credentials(monkeypatch)
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "keywordList": [
            {"relKeyword": "냉커피"},
            None,
            "문자열",
            {"relKeyword": ""},
            {"relKeyword": "   "},
            {"noRelKeyword": "값 없음"},
        ]
    }
    mock_get.return_value = mock_response

    result = fetch_related_keywords("아이스아메리카노")

    assert result == ["냉커피"]


@patch("models.consult.clients.search_ad_api.httpx.get")
def test_fetch_returns_empty_list_when_no_related_keywords(mock_get: MagicMock, monkeypatch) -> None:
    """API 호출은 성공했지만 연관 검색어가 없는 경우 — None(실패)이 아니라 빈 리스트."""
    _set_credentials(monkeypatch)
    mock_response = MagicMock()
    mock_response.json.return_value = {"keywordList": []}
    mock_get.return_value = mock_response

    result = fetch_related_keywords("아이스아메리카노")

    assert result == []


@patch("models.consult.clients.search_ad_api.httpx.get")
def test_fetch_returns_none_when_keyword_list_missing(mock_get: MagicMock, monkeypatch) -> None:
    _set_credentials(monkeypatch)
    mock_response = MagicMock()
    mock_response.json.return_value = {}
    mock_get.return_value = mock_response

    result = fetch_related_keywords("아이스아메리카노")

    assert result is None


@patch("models.consult.clients.search_ad_api.httpx.get")
def test_fetch_returns_none_when_response_is_not_json(mock_get: MagicMock, monkeypatch) -> None:
    _set_credentials(monkeypatch)
    mock_response = MagicMock()
    mock_response.json.side_effect = ValueError("not json")
    mock_get.return_value = mock_response

    result = fetch_related_keywords("아이스아메리카노")

    assert result is None
