from ..graph.state import BasicState


def channel_format_node(state: BasicState) -> dict:
    proposals = []
    for c in state["ranked_copies"]:
        item = {"copy": c.get("copy"), "image_b64": c.get("image_b64")}
        if c.get("error"):
            item["error"] = c["error"]
        proposals.append(item)

    context = state.get("context") or {}
    sources = []
    if context.get("market"):
        sources.append("상권분석")
    if context.get("trend"):
        sources.append("트렌드")
    if context.get("benchmark"):
        sources.append("벤치마크")

    title = state["question"][:30]  # 임시 제목 — 요약 로직으로 교체 필요

    return {
        "status": "ok",
        "sources": sources,
        "tokens_used": state.get("tokens_used", 0),
        "result": {"title": title, "proposals": proposals},
    }
