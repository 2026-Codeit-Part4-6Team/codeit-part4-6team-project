from cache.trend_repo import get_trend

from ..graph.state import BasicState


def trend_for_copy_node(state: BasicState) -> dict:
    """질문과 업종 기준 검색 트렌드(연관 검색어, 날씨 포함)를 조회해
    요약 문장을 context["trend"]에 채운다."""
    trend = get_trend(state["question"])  # keyword는 우선 사용자 원문 전체를 그대로 넣음

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
