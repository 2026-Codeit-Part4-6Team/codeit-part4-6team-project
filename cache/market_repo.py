# 두 챗봇이 공유하는 상권 조회 스텁 — D2에 Cache-Aside로 대체 예정
def get_market(
    lat: float, lng: float, radius: int = 500, industry: str | None = None
) -> dict | None:
    """상권 조회 — D2에 Cache-Aside 실제 구현 예정. 지금은 mock 반환.

    industry가 주어지면 same_industry_count·nearest_distance_m은 해당 업종 기준으로 계산된다.
    industry가 없으면 비교 기준 자체가 없으므로 두 필드 모두 None을 반환한다
    ("경쟁사 0개"라는 확정값과 구분하기 위함).
    """
    if industry is None:
        return {
            "total_count": 40,
            "same_industry_count": None,
            "nearest_distance_m": None,
            "industry_breakdown": {},
        }
    return {
        "total_count": 40,
        "same_industry_count": 10,
        "nearest_distance_m": 60,
        "industry_breakdown": {},
    }
