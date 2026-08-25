from unittest.mock import patch

from models.basic.nodes.seasonality_for_copy import seasonality_for_copy_node


@patch("models.basic.nodes.seasonality_for_copy.compute_seasonality")
def test_seasonality_added_to_context(mock_compute):
    mock_compute.return_value = {
        "reference_date": "2026-08-24",
        "calendar_period": "8월 하순",
        "season_hint": "여름 말기",
    }

    result = seasonality_for_copy_node({"context": {"market": "기존 상권 요약"}})

    assert result["context"]["seasonality"] == {
        "reference_date": "2026-08-24",
        "calendar_period": "8월 하순",
        "season_hint": "여름 말기",
    }
    assert result["context"]["market"] == "기존 상권 요약"