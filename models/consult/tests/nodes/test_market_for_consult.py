# models/consult/nodes/market_for_consult.py 테스트
from unittest.mock import patch

import pytest

from models.consult.nodes.market_for_consult import market_for_consult

_STORE = {
    "name": "카페 코드잇",
    "type": "카페",
    "address": "서울 강남구 역삼동",
    "lat": 37.5,
    "lng": 127.0,
}


def _state() -> dict:
    return {
        "chatbot_type": "consultant",
        "user_id": 1,
        "question": "질문",
        "store": _STORE,
    }


def _market_result(same_industry_count, nearest_distance_m=55) -> dict:
    return {
        "total_count": 43,
        "same_industry_count": same_industry_count,
        "nearest_distance_m": nearest_distance_m,
        "industry_breakdown": {"카페": 12, "편의점": 5},
    }


@patch("models.consult.nodes.market_for_consult.get_market")
def test_calls_get_market_with_store_coordinates_and_type(mock_get_market) -> None:
    mock_get_market.return_value = _market_result(same_industry_count=5)

    market_for_consult(_state())

    mock_get_market.assert_called_once_with(37.5, 127.0, industry="카페")


@patch("models.consult.nodes.market_for_consult.get_market")
def test_returns_none_market_when_get_market_fails(mock_get_market) -> None:
    mock_get_market.return_value = None

    result = market_for_consult(_state())

    assert result == {"context": {"market": None}}


@patch("models.consult.nodes.market_for_consult.get_market")
def test_adds_market_analysis_to_sources_when_successful(mock_get_market) -> None:
    mock_get_market.return_value = _market_result(same_industry_count=5)

    result = market_for_consult(_state())

    assert result["sources"] == ["상권분석"]


@patch("models.consult.nodes.market_for_consult.get_market")
def test_omits_sources_when_get_market_fails(mock_get_market) -> None:
    """실패 시 sources 키 자체를 반환하지 않는다 — 쓰이지 않은 데이터를 근거
    출처로 잘못 표기하면 안 되기 때문이다."""
    mock_get_market.return_value = None

    result = market_for_consult(_state())

    assert "sources" not in result


@patch("models.consult.nodes.market_for_consult.get_market")
def test_preserves_original_fields_and_adds_density_tier(mock_get_market) -> None:
    mock_get_market.return_value = _market_result(same_industry_count=5)

    result = market_for_consult(_state())

    market = result["context"]["market"]
    assert market["total_count"] == 43
    assert market["same_industry_count"] == 5
    assert market["nearest_distance_m"] == 55
    assert market["industry_breakdown"] == {"카페": 12, "편의점": 5}
    assert market["density_tier"] == "보통"


@pytest.mark.parametrize(
    "same_industry_count,expected_tier",
    [
        (None, "판단 불가"),
        (0, "경쟁 없음"),
        (1, "낮음"),
        (3, "낮음"),
        (4, "보통"),
        (8, "보통"),
        (9, "높음"),
        (100, "높음"),
    ],
)
@patch("models.consult.nodes.market_for_consult.get_market")
def test_density_tier_boundaries(mock_get_market, same_industry_count, expected_tier) -> None:
    mock_get_market.return_value = _market_result(same_industry_count=same_industry_count)

    result = market_for_consult(_state())

    assert result["context"]["market"]["density_tier"] == expected_tier
