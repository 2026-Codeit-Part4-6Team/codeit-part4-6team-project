from ..graph.state import BasicState
from ..retrieval.vectorstore import search_benchmark


def benchmark_node(state: BasicState) -> dict:
    """가게 업종(또는 질문)으로 벤치마크 사례를 검색해 context에 추가한다."""
    store = state["store"]
    query = store.get("type") or state["question"]

    try:
        results = search_benchmark(query, k=3)
    # BLE001 억제 사유: 임베딩/인덱스 예외가 나도 벤치마크 없이 계속 진행하도록 개별 실패로 처리
    except Exception:  # noqa: BLE001
        results = []

    context = {**state.get("context", {})}
    if results:
        examples = "; ".join(r["copy"] for r in results)
        context["benchmark"] = f"업종 벤치마크 카피 예시: {examples}"
    else:
        context["benchmark"] = None
    return {"context": context}
