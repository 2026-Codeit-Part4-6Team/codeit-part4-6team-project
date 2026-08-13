from ..graph.state import BasicState
from ..retrieval.vectorstore import search_benchmark


def benchmark_node(state: BasicState) -> dict:
    """가게 업종(또는 질문)으로 벤치마크 사례를 검색해 context에 추가한다."""
    store = state["store"]
    query = store.get("type") or state["question"]
    results = search_benchmark(query, k=3)

    context = {**state.get("context", {})}
    context["benchmark"] = str(results) if results else None
    return {"context": context}
    # search_benchmark() 실제 구현 후, 반환 형식(리스트/딕셔너리)에 맞춰 카피용 문장으로 재요약 필요
