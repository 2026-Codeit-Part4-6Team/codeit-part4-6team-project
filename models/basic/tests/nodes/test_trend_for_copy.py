from unittest.mock import patch

from models.basic.nodes.trend_for_copy import trend_for_copy_node

_STORE = {"name": "카페 코드잇", "type": "카페", "lat": 37.5, "lng": 127.0}


@patch("models.basic.nodes.trend_for_copy.get_trend")
def test_trend_with_related_and_weather_builds_full_summary(mock_get_trend):
    mock_get_trend.return_value = {
        "keyword": "아이스 아메리카노",
        "direction": "상승",
        "related": ["콜드브루", "여름 신메뉴"],
        "weather": {"sky": "맑음", "temp": 29},
    }

    result = trend_for_copy_node(
        {"question": "여름 신메뉴 홍보 문구 만들어줘", "store": _STORE, "context": {}}
    )

    assert result["context"]["trend"] == (
        "'아이스 아메리카노' 검색 트렌드 상승 (연관 검색어: 콜드브루, 여름 신메뉴), 현재 날씨: 맑음 29도"
    )
    mock_get_trend.assert_called_once_with(
        "여름 신메뉴 홍보 문구 만들어줘", industry="카페"
    )


@patch("models.basic.nodes.trend_for_copy.get_trend")
def test_trend_without_weather_omits_weather_clause(mock_get_trend):
    mock_get_trend.return_value = {
        "keyword": "겨울 신메뉴",
        "direction": "하락",
        "related": [],
        "weather": None,
    }

    result = trend_for_copy_node(
        {"question": "겨울 신메뉴", "store": _STORE, "context": {}}
    )

    assert result["context"]["trend"] == "'겨울 신메뉴' 검색 트렌드 하락"


@patch("models.basic.nodes.trend_for_copy.get_trend")
def test_lookup_failure_sets_trend_none_and_keeps_existing_context(mock_get_trend):
    mock_get_trend.return_value = None

    result = trend_for_copy_node(
        {
            "question": "아무거나",
            "store": _STORE,
            "context": {"market": "기존 상권 요약"},
        }
    )

    assert result["context"]["trend"] is None
    assert result["context"]["market"] == "기존 상권 요약"
