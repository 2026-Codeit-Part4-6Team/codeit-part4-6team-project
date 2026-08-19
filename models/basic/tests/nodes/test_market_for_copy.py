from unittest.mock import patch

from models.basic.nodes.market_for_copy import market_for_copy_node

_STORE_WITH_TYPE = {"name": "카페 코드잇", "type": "카페", "lat": 37.5, "lng": 127.0}
_STORE_NO_TYPE = {"name": "카페 코드잇", "lat": 37.5, "lng": 127.0}


@patch("models.basic.nodes.market_for_copy.get_market")
def test_same_industry_present_builds_full_summary(mock_get_market):
    mock_get_market.return_value = {
        "total_count": 43,
        "same_industry_count": 5,
        "nearest_distance_m": 80,
    }

    result = market_for_copy_node({"store": _STORE_WITH_TYPE, "context": {}})

    assert result["context"]["market"] == (
        "반경 내 동일 업종 매장 5곳, 가장 가까운 경쟁 매장까지 80m (전체 매장 43곳 중)"
    )
    mock_get_market.assert_called_once_with(37.5, 127.0, industry="카페")


@patch("models.basic.nodes.market_for_copy.get_market")
def test_store_without_type_passes_none_industry(mock_get_market):
    mock_get_market.return_value = {
        "total_count": 10,
        "same_industry_count": None,
        "nearest_distance_m": None,
    }

    result = market_for_copy_node({"store": _STORE_NO_TYPE, "context": {}})

    mock_get_market.assert_called_once_with(37.5, 127.0, industry=None)
    assert result["context"]["market"] == "반경 내 매장 10곳(업종 비교 정보 없음)"


@patch("models.basic.nodes.market_for_copy.get_market")
def test_zero_same_industry_reports_no_competitors(mock_get_market):
    mock_get_market.return_value = {
        "total_count": 20,
        "same_industry_count": 0,
        "nearest_distance_m": None,
    }

    result = market_for_copy_node({"store": _STORE_WITH_TYPE, "context": {}})

    assert result["context"]["market"] == "반경 내 동일 업종 경쟁 매장 없음(전체 20곳)"


@patch("models.basic.nodes.market_for_copy.get_market")
def test_lookup_failure_sets_market_none_and_keeps_existing_context(mock_get_market):
    mock_get_market.return_value = None

    result = market_for_copy_node(
        {"store": _STORE_WITH_TYPE, "context": {"trend": "기존 트렌드 요약"}}
    )

    assert result["context"]["market"] is None
    assert result["context"]["trend"] == "기존 트렌드 요약"
