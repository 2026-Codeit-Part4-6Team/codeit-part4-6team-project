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
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

from models.basic.graph.build_basic import build_basic_graph
from models.basic.main import assemble_response
from models.shared.eval_fixtures import build_model_request
from models.shared.llm import call_llm
from models.shared.config import OPENAI_MODEL

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

_graph = None


def _get_graph():
    """그래프를 1회만 컴파일해 재사용한다(pilot_judge_stability.py가
    generate_one()을 문항마다 반복 호출하므로 매번 새로 컴파일하면 낭비다)."""
    global _graph
    if _graph is None:
        _graph = build_basic_graph()
    return _graph


def reset_graph() -> None:
    """테스트에서 캐시된 그래프를 비운다."""
    global _graph
    _graph = None


def _fake_get_market(lat, lng, radius=500, industry=None):
    return _MARKET_FIXTURE


def _fake_get_trend(keyword, industry=None):
    return {**_TREND_FIXTURE, "keyword": keyword}


def _fake_generate_image(prompt: str, size: str = "1024x1024") -> str:
    """1x1 흰 픽셀 PNG — 실제 이미지 API를 태우지 않고 디코딩만 통과시킨다.
    골든 데이터셋 rubric은 텍스트 카피만 채점하므로 이미지 품질은 무관하다(§7)."""
    import base64
    import io

    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", (1, 1), "white").save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


def generate_one_with_context(item: dict) -> tuple[dict, dict]:
    """generate_one()과 같은 경로를 타되, Faithfulness 채점에 쓸 실행 중
    컨텍스트(state["context"] — market/trend/benchmark)도 함께 반환한다(§6.2).

    문항 작성 시점에 컨텍스트를 미리 적으면 파이프라인이 바뀔 때마다 60문항을
    고쳐야 하므로, §6.2 설계대로 런타임에 캡처한다.
    """
    request = build_model_request(item)
    with (
        patch(
            "models.basic.nodes.market_for_copy.get_market",
            side_effect=_fake_get_market,
        ),
        patch(
            "models.basic.nodes.trend_for_copy.get_trend", side_effect=_fake_get_trend
        ),
        patch(
            "models.basic.nodes.image_gen.generate_image",
            side_effect=_fake_generate_image,
        ),
    ):
        final_state = _get_graph().invoke(request)

    return assemble_response(final_state), (final_state.get("context") or {})


def generate_one(item: dict) -> dict:
    """골든 데이터셋 문항 하나를 실제 파이프라인으로 실행해 서비스 응답만 반환한다.

    pilot_judge_stability.py가 응답만 필요로 하므로 하위 호환용으로 남긴다 —
    context_snapshot까지 필요하면 generate_one_with_context()를 쓴다.
    """
    return generate_one_with_context(item)[0]


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


def _judge_faithfulness(response: dict, context_snapshot: dict) -> int | None:
    """카피가 실행 중 캡처한 컨텍스트(상권·트렌드·벤치마크)에 근거했는가(§6.2).

    컨텍스트가 비었거나(예: reask로 채널 이후 노드를 안 탄 경우) 카피가 없으면
    채점 대상이 없으므로 None을 반환한다.
    """
    proposals_text = "\n".join(
        f"- {p.get('copy')}" for p in response.get("proposals", []) if p.get("copy")
    )
    if not context_snapshot or not proposals_text:
        return None

    prompt = (
        f"## 참고 컨텍스트(상권·트렌드·벤치마크)\n"
        f"{json.dumps(context_snapshot, ensure_ascii=False)}\n\n"
        f"## 생성된 카피\n{proposals_text}\n\n"
        "카피가 위 컨텍스트에 실제로 근거하고 있는가? 컨텍스트에 없는 수치·사실을 "
        "지어냈다면 낮은 점수를 준다. 1~5점 정수로 평가하라.\n"
        'JSON으로만 답하라: {"score": 정수}'
    )
    raw, _tokens = call_llm(
        "너는 광고 카피가 주어진 근거 자료에 실제로 부합하는지 검증하는 심사위원이다.",
        prompt,
        json_mode=True,
    )
    return int(json.loads(raw)["score"])


def _judge_answer_relevance(item: dict, response: dict) -> int | None:
    """카피가 사용자 질문의 의도에 실제로 맞는 답인가(§6, Answer Relevance)."""
    proposals_text = "\n".join(
        f"- {p.get('copy')}" for p in response.get("proposals", []) if p.get("copy")
    )
    if not proposals_text:
        return None

    prompt = (
        f"## 사용자 질문\n{item['question']}\n\n## 생성된 카피\n{proposals_text}\n\n"
        "카피가 사용자 질문의 의도에 실제로 맞는 답인가? 1~5점 정수로 평가하라.\n"
        'JSON으로만 답하라: {"score": 정수}'
    )
    raw, _tokens = call_llm(
        "너는 답변이 질문 의도에 맞는지 평가하는 심사위원이다.",
        prompt,
        json_mode=True,
    )
    return int(json.loads(raw)["score"])


def run(dataset_path: Path, area: str, items_limit: int | None = None) -> dict:
    """골든 데이터셋 전체(area 필터)를 순회하며 채점하고 리포트를 저장한다."""
    items = [
        i
        for i in json.loads(dataset_path.read_text(encoding="utf-8"))
        if i["area"] == area
    ]
    if items_limit is not None:
        items = items[:items_limit]
    if not items:
        print(f"{area} 문항이 없습니다.", file=sys.stderr)
        sys.exit(1)

    results = []
    latencies = []
    errors = []

    for item in items:
        start = time.monotonic()
        try:
            response, context_snapshot = generate_one_with_context(item)
        except Exception as exc:  # noqa: BLE001 — 문항 하나 실패로 전체를 죽이지 않는다
            errors.append({"id": item["id"], "error": f"{type(exc).__name__}: {exc}"})
            results.append({
                "id": item["id"],
                "passed": False,
                "checks": {},
                "scores": {},
                "faithfulness": None,
                "answer_relevance": None,
                "response": None,
                "context_snapshot": {},
                "generated": False,
            })
            continue
        latencies.append(time.monotonic() - start)

        checks = _rule_based_checks(item, response)
        ok = all(checks.values())
        scores = _judge_rubric(item, response) if ok else {}
        faithfulness = _judge_faithfulness(response, context_snapshot) if ok else None
        answer_relevance = _judge_answer_relevance(item, response) if ok else None

        results.append(
            {
                "id": item["id"],
                "passed": ok,
                "checks": checks,
                "scores": scores,
                "faithfulness": faithfulness,
                "answer_relevance": answer_relevance,
                "response": response,
                "context_snapshot": context_snapshot,
                "generated": True,
            }
        )
        time.sleep(1)

    processed = len(results)
    print(f"{area} {len(items)}문항 중 {processed}건 처리 (생성 실패 {len(errors)}건)")
    if errors:
        print(f"실패 문항: {[e['id'] for e in errors]}", file=sys.stderr)

    all_scores = [s for r in results for s in r["scores"].values()]

    scores_by_criterion = defaultdict(list)
    for r in results:
        for k, v in r["scores"].items():
            scores_by_criterion[k].append(v)
    llm_judge_by_criterion = {
        k: round(sum(v) / len(v), 2) for k, v in scores_by_criterion.items()
    }

    faithfulness_scores = [r["faithfulness"] for r in results if r["faithfulness"] is not None]
    answer_relevance_scores = [
        r["answer_relevance"] for r in results if r["answer_relevance"] is not None
    ]

    report = {
        "run_at": datetime.now(UTC).isoformat(),
        "area": area,
        "model": "gpt-4.1-mini",
        "item_count": processed,
        "generation_failures": errors,
        "metrics": {
            "llm_judge_avg": (
                round(sum(all_scores) / len(all_scores), 2) if all_scores else None
            ),
            "llm_judge_by_criterion": llm_judge_by_criterion,
            "faithfulness_avg": (
                round(sum(faithfulness_scores) / len(faithfulness_scores), 2)
                if faithfulness_scores else None
            ),
            "answer_relevance_avg": (
                round(sum(answer_relevance_scores) / len(answer_relevance_scores), 2)
                if answer_relevance_scores else None
            ),
            "contract_compliance": round(
                sum(r["passed"] for r in results) / processed, 2
            ),
            "failure_rate": round(sum(not r["passed"] for r in results) / processed, 2),
            "latency_p50_s": (
                round(sorted(latencies)[len(latencies) // 2], 2) if latencies else None
            ),
        },
        "items": results,
    }

    out_dir = Path("models/basic/eval/reports")
    out_dir.mkdir(parents=True, exist_ok=True)
    today = datetime.now(UTC).date()
    out_path = out_dir / f"{today}.json"
    n = 2
    while out_path.exists():
        out_path = out_dir / f"{today}-{n}.json"
        n += 1
    out_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"결과 저장: {out_path}")
    return report

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--area", default="basic")
    parser.add_argument("--items", type=int, default=None, help="테스트용 문항 수 제한")
    args = parser.parse_args()
    run(args.dataset, args.area, args.items)