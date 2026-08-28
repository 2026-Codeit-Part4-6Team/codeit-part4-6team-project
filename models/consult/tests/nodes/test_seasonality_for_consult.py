# models/consult/nodes/seasonality_for_consult.py 테스트
from unittest.mock import patch

from models.consult.nodes.seasonality_for_consult import seasonality_for_consult

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


@patch("models.consult.nodes.seasonality_for_consult.compute_seasonality")
def test_returns_only_context_seasonality(mock_compute) -> None:
    """State에서 아무 값도 읽지 않고 context["seasonality"]만 반환한다 — sources에는
    추가하지 않는다(외부 데이터 출처가 아니라 요청일에서 계산한 내부 힌트라서)."""
    mock_compute.return_value = {
        "reference_date": "2026-08-24",
        "calendar_period": "8월 하순",
        "season_hint": "여름",
    }

    result = seasonality_for_consult(_state())

    assert result == {
        "context": {
            "seasonality": {
                "reference_date": "2026-08-24",
                "calendar_period": "8월 하순",
                "season_hint": "여름",
            }
        }
    }
    mock_compute.assert_called_once_with()
