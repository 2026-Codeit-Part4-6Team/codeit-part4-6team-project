from cache.trend_repo import get_trend
from ..graph.state import BasicState


def trend_for_copy_node(state: BasicState) -> dict:
    store = state["store"]
    trend = get_trend(state["question"], industry=store.get("type")) # keyword는 우선 사용자 원문 전체를 그대로 넣음

    context = {**state.get("context", {})}

    if not trend:
        context["trend"] = None
        return {"context": context}

    summary = f"'{trend['keyword']}' 검색 트렌드 {trend['direction']}"
    if trend.get("related"):
        summary += f" (연관 검색어: {', '.join(trend['related'])})"
    if trend.get("weather"):
        w = trend["weather"]
        summary += f", 현재 날씨: {w.get('sky')} {w.get('temp')}도"

    context["trend"] = summary
    return {"context": context}