"""골든 데이터셋 area=basic 문항을 실제 파이프라인으로 실행해 채점한다.

실행: uv run python models/basic/eval/eval_generation.py --dataset shared_data/golden_dataset.json --area basic

규칙 기반 지표(계약 준수율·must_include/exclude)는 LLM 호출 없이 즉시 판정하고,
rubric 점수만 LLM Judge(GPT-5.4 Mini)로 채점한다. 상권·트렌드는 고정 fixture로
모킹해 평가 실행 중 외부 API를 호출하지 않는다(§1.4 재현성 원칙, §10.3 DoD ④).
"""

import argparse
import json
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

from models.basic.graph.build_basic import build_basic_graph
from models.basic.main import assemble_response
from models.shared.eval_fixtures import build_model_request
from models.shared.llm import call_llm

JUDGE_MODEL = "gpt-5.4-mini"

_MARKET_FIXTURE = {
    "total_count": 6691,
    "same_industry_count": 177,
    "nearest_distance_m": 80,
}

_TREND_FIXTURE = {
    "keyword": "카페",
    "direction": "유지",
    "related": [],
}


def _fake_get_market(lat, lng, radius=500, industry=None):
    return _MARKET_FIXTURE


def _fake_get_trend(keyword, industry=None):
    return {**_TREND_FIXTURE, "keyword": keyword}


def _judge_action(expected_action: str, response: dict) -> bool:
    """expected.action 과 모델 응답을 비교한다(golden_dataset.md §4.6)."""
    status = response.get("status")
    if expected_action == "pass":
        return status == "ok"
    if status != "blocked":
        return False
    return response.get("action") == expected_action


def _rule_based_checks(item: dict, response: dict) -> dict:
    """LLM 호출 없이 즉시 판정 가능한 항목들을 검사한다."""
    expected = item["expected"]
    checks = {"action_match": _judge_action(expected["action"], response)}

    if expected["action"] != "pass":
        return checks

    proposals = response.get("proposals", [])
    checks["must_have_fields"] = all(
        k in response for k in expected.get("must_have_fields", [])
    )
    checks["proposal_count"] = len(proposals) == expected.get("proposal_count", 3)

    all_copy = " ".join(p.get("copy") or "" for p in proposals)
    must_any = expected.get("must_include_any")
    checks["must_include_any"] = (not must_any) or any(
        kw in all_copy for kw in must_any
    )

    must_not = expected.get("must_not_include", [])
    checks["must_not_include"] = not any(kw in all_copy for kw in must_not)

    return checks


def _judge_rubric(item: dict, response: dict) -> dict:
    """rubric 항목별로 LLM Judge에게 1~5점을 매기게 한다."""
    rubric = item["expected"].get("rubric")
    if not rubric:
        return {}

    proposals_text = "\n".join(
        f"- {p.get('copy')}" for p in response.get("proposals", []) if p.get("copy")
    )
    format_hint = "{" + ", ".join(f'"{k}": 0' for k in rubric) + "}"
    prompt = (
        f"질문: {item['question']}\n\n생성된 카피 후보:\n{proposals_text}\n\n"
        "아래 평가 기준마다 1~5점을 매겨라. JSON으로만 답하라.\n"
        + "\n".join(f"- {k}: {v}" for k, v in rubric.items())
        + f"\n\n형식: {format_hint}"
    )
    raw, _tokens = call_llm(
        "너는 광고 카피 심사위원이다. 각 기준에 1~5점을 매긴다.",
        prompt,
        json_mode=True,
    )
    return json.loads(raw)


def run(dataset_path: Path, area: str) -> dict:
    items = [
        i
        for i in json.loads(dataset_path.read_text(encoding="utf-8"))
        if i["area"] == area
    ]
    if not items:
        print(f"{area} 문항이 없습니다.", file=sys.stderr)
        sys.exit(1)

    graph = build_basic_graph()
    results = []
    latencies = []

    with (
        patch(
            "models.basic.nodes.market_for_copy.get_market",
            side_effect=_fake_get_market,
        ),
        patch(
            "models.basic.nodes.trend_for_copy.get_trend", side_effect=_fake_get_trend
        ),
    ):
        for item in items:
            request = build_model_request(item)
            start = time.monotonic()
            final_state = graph.invoke(request)
            latencies.append(time.monotonic() - start)

            response = assemble_response(final_state)
            checks = _rule_based_checks(item, response)
            scores = _judge_rubric(item, response) if all(checks.values()) else {}

            results.append(
                {
                    "id": item["id"],
                    "passed": all(checks.values()),
                    "checks": checks,
                    "scores": scores,
                    "response": response,
                    "context_snapshot": final_state.get("context"),
                }
            )
            time.sleep(1)  # 직렬 실행 + 요청 간 sleep (§10.4 예산 주의)

    processed = len(results)
    if processed != len(items):
        print(
            f"{area} {len(items)}문항 중 {processed}건 처리 — 불일치", file=sys.stderr
        )
        sys.exit(1)
    print(f"{area} {len(items)}문항 중 {processed}건 처리")

    all_scores = [s for r in results for s in r["scores"].values()]
    report = {
        "run_at": datetime.now(UTC).isoformat(),
        "area": area,
        "model": JUDGE_MODEL,
        "item_count": processed,
        "metrics": {
            "llm_judge_avg": (
                round(sum(all_scores) / len(all_scores), 2) if all_scores else None
            ),
            "contract_compliance": round(
                sum(r["passed"] for r in results) / processed, 2
            ),
            "failure_rate": round(sum(not r["passed"] for r in results) / processed, 2),
            "latency_p50_s": round(sorted(latencies)[len(latencies) // 2], 2),
        },
        "items": results,
    }

    out_dir = Path("models/basic/eval/reports")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{datetime.now(UTC).date()}.json"
    out_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"결과 저장: {out_path}")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--area", default="basic")
    args = parser.parse_args()
    run(args.dataset, args.area)
