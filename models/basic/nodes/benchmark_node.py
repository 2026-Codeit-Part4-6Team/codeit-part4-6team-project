from ..graph.state import BasicState
from ..retrieval.vectorstore import search_benchmark


def benchmark_node(state: BasicState) -> dict:
    """가게 업종(또는 질문)으로 벤치마크 사례를 검색해 context에 추가한다."""
    store = state["store"]
    query = store.get("type") or state["question"]
    results = search_benchmark(query, k=3)

    context = {**state.get("context", {})}
    if results:
        examples = "; ".join(r["copy"] for r in results)
        context["benchmark"] = f"업종 벤치마크 카피 예시: {examples}"
    else:
        context["benchmark"] = None
    return {"context": context}