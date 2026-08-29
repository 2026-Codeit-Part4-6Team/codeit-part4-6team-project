from models.shared.seasonality import compute_seasonality

from ..graph.state import BasicState


def seasonality_for_copy_node(state: BasicState) -> dict:
    """요청 날짜 기준 계절성 힌트를 조회해 context["seasonality"]에 채운다.
    외부 API·LLM 호출이 없는 순수 계산이라 실패 케이스가 없다."""
    context = {**state.get("context", {})}
    context["seasonality"] = compute_seasonality()
    return {"context": context}
