# models/consult/nodes/trend_for_consult.py 테스트
from unittest.mock import patch

from models.consult.nodes.trend_for_consult import trend_for_consult

_STORE = {
    "name": "카페 코드잇",
    "type": "카페",
    "address": "서울 강남구 역삼동",
    "lat": 37.5,
    "lng": 127.0,
}


def _state(keyword: str | None) -> dict:
    return {
        "chatbot_type": "consultant",
        "user_id": 1,
        "question": "질문",
        "store": _STORE,
        "context": {"question_analysis": {"is_sufficient": True, "missing_info": [], "keyword": keyword}},
    }


def _trend_result() -> dict:
    return {
        "keyword": "아이스아메리카노",
        "direction": "상승",
        "related": ["냉커피", "여름음료"],
    }


@patch("models.consult.nodes.trend_for_consult.get_trend")
def test_calls_get_trend_with_keyword_and_store_type(mock_get_trend) -> None:
    mock_get_trend.return_value = _trend_result()

    trend_for_consult(_state(keyword="아이스아메리카노"))

    mock_get_trend.assert_called_once_with("아이스아메리카노", industry="카페")


@patch("models.consult.nodes.trend_for_consult.get_trend")
def test_returns_none_trend_when_keyword_is_missing(mock_get_trend) -> None:
    """keyword가 없으면(질문에 특정 대상이 없음) 조회할 이유가 없어 API를 부르지 않는다."""
    result = trend_for_consult(_state(keyword=None))

    mock_get_trend.assert_not_called()
    assert result == {"context": {"trend": None}}


@patch("models.consult.nodes.trend_for_consult.get_trend")
def test_returns_none_trend_when_get_trend_fails(mock_get_trend) -> None:
    mock_get_trend.return_value = None

    result = trend_for_consult(_state(keyword="아이스아메리카노"))

    assert result == {"context": {"trend": None}}


@patch("models.consult.nodes.trend_for_consult.get_trend")
def test_passes_through_trend_result_unchanged(mock_get_trend) -> None:
    """상권처럼 등급으로 가공하지 않고 get_trend() 결과를 그대로 전달한다 —
    direction/related 자체가 이미 컨설팅에 쓸 수 있는 형태라 추가 해석이 불필요하고,
    근거 없는 임의 등급을 만들면 오히려 전략 노드가 지어낸 근거를 쓸 위험이 있다."""
    mock_get_trend.return_value = _trend_result()

    result = trend_for_consult(_state(keyword="아이스아메리카노"))

    assert result["context"] == {"trend": _trend_result()}


@patch("models.consult.nodes.trend_for_consult.get_trend")
def test_adds_trend_to_sources_when_successful(mock_get_trend) -> None:
    mock_get_trend.return_value = _trend_result()

    result = trend_for_consult(_state(keyword="아이스아메리카노"))

    assert result["sources"] == ["트렌드"]


@patch("models.consult.nodes.trend_for_consult.get_trend")
def test_omits_sources_when_get_trend_fails(mock_get_trend) -> None:
    mock_get_trend.return_value = None

    result = trend_for_consult(_state(keyword="아이스아메리카노"))

    assert "sources" not in result


def test_omits_sources_when_keyword_is_missing() -> None:
    result = trend_for_consult(_state(keyword=None))

    assert "sources" not in result


def test_returns_none_trend_when_context_missing() -> None:
    """question_analysis가 어떤 이유로든 context를 못 채운 극단적인 경우에도
    예외 없이 안전하게 처리한다."""
    state = {
        "chatbot_type": "consultant",
        "user_id": 1,
        "question": "질문",
        "store": _STORE,
    }

    result = trend_for_consult(state)

    assert result == {"context": {"trend": None}}
