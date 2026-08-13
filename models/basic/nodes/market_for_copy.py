from cache.market_repo import get_market

from ..graph.state import BasicState


def market_for_copy_node(state: BasicState) -> dict:
    store = state["store"]
    market = get_market(store["lat"], store["lng"], industry=store.get("type"))

    context = {**state.get("context", {})}

    if not market:
        context["market"] = None
        return {"context": context}

    same_industry = market.get("same_industry_count")
    nearest = market.get("nearest_distance_m")

    if same_industry is None:
        summary = f"반경 내 매장 {market['total_count']}곳(업종 비교 정보 없음)"
    elif same_industry == 0:
        summary = f"반경 내 동일 업종 경쟁 매장 없음(전체 {market['total_count']}곳)"
    else:
        summary = (
            f"반경 내 동일 업종 매장 {same_industry}곳, "
            f"가장 가까운 경쟁 매장까지 {nearest}m "
            f"(전체 매장 {market['total_count']}곳 중)"
        )

    context["market"] = summary
    return {"context": context}
