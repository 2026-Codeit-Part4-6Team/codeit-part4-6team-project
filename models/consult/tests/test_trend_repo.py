# trend_repo 조회 스텁 테스트
from cache.trend_repo import get_trend


def test_get_trend_returns_expected_keys() -> None:
    """D1 스텁은 기본 챗봇 담당자가 바로 참조할 필드를 mock으로 반환한다."""
    result = get_trend("아이스아메리카노")

    assert set(result.keys()) == {"keyword", "direction", "related", "weather"}
    assert result["keyword"] == "아이스아메리카노"
    assert isinstance(result["related"], list)
