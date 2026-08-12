# 두 챗봇이 공유하는 트렌드 조회 스텁 — D5에 Cache-Aside로 대체 예정
def get_trend(keyword: str, industry: str | None = None) -> dict | None:
    """검색어 트렌드 조회 — D5에 Cache-Aside 실제 구현 예정. 지금은 mock 반환."""
    return {
        "keyword": keyword,
        "direction": "유지",
        "related": [],
        "weather": None,
    }
