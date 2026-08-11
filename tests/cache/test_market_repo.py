# market_repo 조회 스텁 테스트
from cache.market_repo import get_market


def test_get_market_returns_expected_keys() -> None:
    """D1 스텁은 기본 챗봇 담당자가 바로 참조할 필드를 mock으로 반환한다."""
    result = get_market(37.5, 127.0)

    assert set(result.keys()) == {
        "total_count",
        "same_industry_count",
        "nearest_distance_m",
        "industry_breakdown",
    }
    assert isinstance(result["total_count"], int)
    assert isinstance(result["industry_breakdown"], dict)


def test_get_market_without_industry_has_undefined_same_industry_fields() -> None:
    """industry가 없으면 비교 기준이 없으므로 same_industry_count·nearest_distance_m 모두 None.

    "경쟁사 0개"라는 확정값과 "모름"을 구분해야 잘못된 마케팅 근거로 이어지지 않는다.
    """
    result = get_market(37.5, 127.0)

    assert result["same_industry_count"] is None
    assert result["nearest_distance_m"] is None


def test_get_market_accepts_industry() -> None:
    """industry를 넘기면 해당 업종 기준의 값을 반환한다."""
    result = get_market(37.5, 127.0, industry="카페")

    assert set(result.keys()) == {
        "total_count",
        "same_industry_count",
        "nearest_distance_m",
        "industry_breakdown",
    }
    assert isinstance(result["same_industry_count"], int)
    assert isinstance(result["nearest_distance_m"], int)
