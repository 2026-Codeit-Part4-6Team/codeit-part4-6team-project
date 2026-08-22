from cache.trend_repo import get_trend

from ..graph.state import BasicState


def trend_for_copy_node(state: BasicState) -> dict:
    """업종과 keyword(question_analysis가 추출한 검색 키워드) 기준 검색
    트렌드(연관 검색어)를 조회해 요약 문장을 context["trend"]에 채운다.

    keyword가 없으면 API를 호출하지 않는다(D-079·D-201). 질문 원문을
    검색어로 쓰면 캐시 키가 매번 달라 적중률이 0%가 되어 NAVER 월 5만
    건 한도를 직접 소모한다 — 컨설턴트 쪽과 동일하게 처리한다.
    """
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
