from cache.trend_repo import get_trend

from ..graph.state import BasicState


def trend_for_copy_node(state: BasicState) -> dict:
    """업종과 keyword(question_analysis가 추출한 검색 키워드) 기준 검색
    트렌드(연관 검색어)를 조회해 요약 문장을 context["trend"]에
    채운다. keyword가 없으면 질문 원문으로 폴백한다."""
    keyword = state.get("keyword")
    context = {**state.get("context", {})}

    if not keyword:
        context["trend"] = None
        return {"context": context}

    store = state["store"]
    trend = get_trend(keyword, industry=store.get("type"))

    if not trend:
        context["trend"] = None
        return {"context": context}

    summary = f"'{trend['keyword']}' 검색 트렌드 {trend['direction']}"
    if trend.get("related"):
        summary += f" (연관 검색어: {', '.join(trend['related'])})"

    context["trend"] = summary
    return {"context": context}
