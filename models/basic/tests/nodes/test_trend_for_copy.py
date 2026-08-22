from unittest.mock import patch

from models.basic.nodes.trend_for_copy import trend_for_copy_node

_STORE = {"name": "카페 코드잇", "type": "카페", "lat": 37.5, "lng": 127.0}


@patch("models.basic.nodes.trend_for_copy.get_trend")
def test_trend_with_related_builds_full_summary(mock_get_trend):
    mock_get_trend.return_value = {
        "keyword": "아이스 아메리카노",
        "direction": "상승",
        "related": ["콜드브루", "여름 신메뉴"],
    }

    result = trend_for_copy_node(
        {
            "question": "여름 신메뉴 홍보 문구 만들어줘",
            "keyword": "여름 신메뉴",
            "store": _STORE,
            "context": {},
        }
    )

    assert result["context"]["trend"] == (
        "'아이스 아메리카노' 검색 트렌드 상승 (연관 검색어: 콜드브루, 여름 신메뉴)"
    )
    mock_get_trend.assert_called_once_with("여름 신메뉴", industry="카페")


@patch("models.basic.nodes.trend_for_copy.get_trend")
def test_trend_without_related_omits_related_clause(mock_get_trend):
    mock_get_trend.return_value = {
        "keyword": "겨울 신메뉴",
        "direction": "하락",
        "related": [],
    }

    result = trend_for_copy_node(
        {
            "question": "겨울 신메뉴",
            "keyword": "겨울 신메뉴",
            "store": _STORE,
            "context": {},
        }
    )

    assert result["context"]["trend"] == "'겨울 신메뉴' 검색 트렌드 하락"


@patch("models.basic.nodes.trend_for_copy.get_trend")
def test_lookup_failure_sets_trend_none_and_keeps_existing_context(mock_get_trend):
    mock_get_trend.return_value = None

    result = trend_for_copy_node(
        {
            "question": "아무거나",
            "keyword": "아무거나 키워드",
            "store": _STORE,
            "context": {"market": "기존 상권 요약"},
        }
    )

    assert result["context"]["trend"] is None
    assert result["context"]["market"] == "기존 상권 요약"


@patch("models.basic.nodes.trend_for_copy.get_trend")
def test_missing_keyword_skips_api_call_and_returns_none(mock_get_trend):
    """D-079·D-201: keyword가 없으면 질문 원문으로 폴백하지 않고 API 자체를 안 부른다.
    원문을 검색어로 쓰면 캐시 적중률이 0%가 되어 NAVER 월 5만 건 한도를 직접 소모한다."""
    result = trend_for_copy_node(
        {"question": "아무거나", "store": _STORE, "context": {}}
    )

    mock_get_trend.assert_not_called()
    assert result["context"]["trend"] is None