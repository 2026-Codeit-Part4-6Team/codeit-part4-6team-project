"""검색 평가셋(RT-)으로 벤치마크 RAG의 Hit Rate@5 · MRR을 측정한다.

실행: uv run python models/basic/eval/eval_retrieval.py --dataset shared_data/retrieval_eval.json

"""

import argparse
import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

from models.basic.retrieval.vectorstore import search_benchmark

TOP_K = 5


def _dataset_version(dataset_path: Path) -> str:
    """데이터셋 파일 내용 해시로 버전 라벨을 만든다 — 하드코딩된 버전 문자열이
    실제 파일 내용과 어긋나는 사고(eval_refusal에서 발생)를 방지한다."""
    digest = hashlib.sha256(dataset_path.read_bytes()).hexdigest()[:8]
    return f"auto-{digest}"


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
    errors = []
    for item in items:
        try:
            retrieved = search_benchmark(item["query"], k=TOP_K)
        # BLE001 억제 사유: 문항 하나의 검색 실패로 전체 평가를 죽이지 않는다
        except Exception as exc:  # noqa: BLE001
            errors.append({"id": item["id"], "error": f"{type(exc).__name__}: {exc}"})
            continue

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
    print(f"{len(items)}문항 중 {processed}건 처리 (검색 실패 {len(errors)}건)")
    if errors:
        print(f"실패 문항: {[e['id'] for e in errors]}", file=sys.stderr)

    if processed == 0:
        print("전 문항 검색 실패 — 평가할 결과가 없습니다.", file=sys.stderr)
        sys.exit(1)

    hit_rate = sum(r["hit"] for r in results) / processed
    mrr = sum(r["reciprocal_rank"] for r in results) / processed

    report = {
        "run_at": datetime.now(UTC).isoformat(),
        "area": "retrieval",
        "dataset_version": _dataset_version(dataset_path),
        "item_count": processed,
        "generation_failures": errors,
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
