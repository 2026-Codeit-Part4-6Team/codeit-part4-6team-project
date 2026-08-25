"""검색 평가셋(RT-)으로 벤치마크 RAG의 Hit Rate@5 · MRR을 측정한다.

실행: uv run python models/basic/eval/eval_retrieval.py --dataset shared_data/retrieval_eval.json

"""

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

from models.basic.retrieval.vectorstore import search_benchmark

TOP_K = 5


def _hit_at_k(relevant_ids: list[str], retrieved_ids: list[str]) -> bool:
    return any(doc_id in retrieved_ids for doc_id in relevant_ids)


def _reciprocal_rank(relevant_ids: list[str], retrieved_ids: list[str]) -> float:
    for rank, doc_id in enumerate(retrieved_ids, start=1):
        if doc_id in relevant_ids:
            return 1 / rank
    return 0.0


def run(dataset_path: Path) -> dict:
    items = json.loads(dataset_path.read_text(encoding="utf-8"))

    results = []
    for item in items:
        retrieved = search_benchmark(item["query"], k=TOP_K)
        retrieved_ids = [r["id"] for r in retrieved]

        results.append(
            {
                "id": item["id"],
                "query": item["query"],
                "retrieved_ids": retrieved_ids,
                "relevant_document_ids": item["relevant_document_ids"],
                "hit": _hit_at_k(item["relevant_document_ids"], retrieved_ids),
                "reciprocal_rank": _reciprocal_rank(
                    item["relevant_document_ids"], retrieved_ids
                ),
            }
        )

    processed = len(results)
    if processed != len(items):
        print(f"{len(items)}문항 중 {processed}건 처리 — 불일치", file=sys.stderr)
        sys.exit(1)
    print(f"{len(items)}문항 중 {processed}건 처리")

    hit_rate = sum(r["hit"] for r in results) / processed
    mrr = sum(r["reciprocal_rank"] for r in results) / processed

    report = {
        "run_at": datetime.now(UTC).isoformat(),
        "area": "retrieval",
        "dataset_version": "v1.2",
        "item_count": processed,
        "metrics": {
            f"hit_rate_at_{TOP_K}": round(hit_rate, 3),
            "mrr": round(mrr, 3),
        },
        "items": results,
    }

    out_dir = Path("models/basic/eval/reports")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"retrieval_{datetime.now(UTC).date()}.json"
    out_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"결과 저장: {out_path}")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, required=True)
    args = parser.parse_args()
    run(args.dataset)
