#!/usr/bin/env python
"""
models/shared/eval/pilot_judge_stability.py
— Judge 재현성 파일럿 (D-276 설계 · D-298 판정 기준)

    uv run python -m models.shared.eval.pilot_judge_stability --area consult
    uv run python -m models.shared.eval.pilot_judge_stability --area basic

★ 왜 "5문항 1회"로는 부족한가
  파일럿의 목적은 점수의 절대값이 아니라 **자[尺]가 흔들리지 않는지** 확인하는 것이다.
  생성과 채점을 매번 새로 돌리면 점수 차이가
    · 생성이 매번 달라서인지 (LLM_TEMPERATURE=0.3)
    · Judge 가 매번 달라서인지
  구분할 수 없다. 기준 문서 §11.2.2 의 "한 번에 하나만 바꾼다"와 같은 논리다.

★ 그래서 이렇게 측정한다
  1) 문항별로 생성을 **1회만** 돌려 응답을 고정한다
  2) 그 고정된 응답을 Judge 에 **3회** 태운다
  3) 판정은 judge_stability.evaluate_stability() 에 넘긴다 ← ★ 이 파일은 판정하지 않는다

★ 판정 로직을 여기 두지 않는 이유 (D-298 반영)
  기준이 바뀔 때마다 파일럿을 고쳐야 하고, 기본·컨설턴트가 서로 다른 기준으로
  통과하게 된다. 이 파일은 '측정', judge_stability 는 '판정' 만 맡는다.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import statistics
import sys
from pathlib import Path

from models.shared.config import (
    LLM_JUDGE_TEMPERATURE,
    OPENAI_JUDGE_MODEL,
    OPENAI_MODEL,
)
from models.shared.eval.judge_stability import evaluate_stability, format_report
from models.shared.eval.token_usage import (
    build_token_usage,
    item_token_delta,
    preflight,
    token_snapshot,
)
from models.shared.llm import call_llm

JUDGE_REPEAT = 3
PILOT_ITEM_COUNT = 5
DATASET = Path("shared_data/golden_dataset.json")

# area → (생성 함수 모듈경로, 함수명, 결과 저장 경로)
_GENERATORS = {
    "basic": ("models.basic.eval.eval_generation", "generate_one",
              "models/basic/eval/reports/pilot_judge_stability.json"),
    "consult": ("models.consult.eval.eval_strategy", "generate_one",
                "models/consult/eval/reports/pilot_judge_stability.json"),
}

# ★ 이 프롬프트가 곧 '자[尺]' 다. 파일럿과 본 평가가 반드시 같아야 하므로
#   해시를 결과 파일에 남긴다 — 다르면 파일럿 결과가 본 평가에 전이되지 않는다.
JUDGE_SYSTEM = """너는 소상공인 대상 AI 서비스의 응답 평가자다.
주어진 rubric 항목마다 1~5점의 정수를 매긴다.
근거 없이 후하게 주지 않는다. 애매하면 낮은 쪽을 준다.
rubric 에 있는 항목만, 전부 채점한다. 항목을 빼거나 새로 만들지 않는다.
JSON 만 출력한다: {"scores": {"항목명": 정수, ...}}"""


def _judge_once(question: str, response: dict, rubric: dict[str, str]) -> dict[str, int]:
    """★ 반드시 temperature=0 으로 호출한다(D-275).

    Judge 가 rubric 항목을 빠뜨리거나 없는 항목을 만들어도 파일럿 전체가
    죽지 않도록, 반환값을 rubric 키 기준으로 정규화한다.
    """
    user = (
        f"## 사용자 요청\n{question}\n\n"
        f"## 모델 응답\n{json.dumps(response, ensure_ascii=False, indent=2)}\n\n"
        f"## 채점 기준\n"
        + "\n".join(f"- {k}: {v}" for k, v in rubric.items())
        + "\n\n## 출력\nJSON 만."
    )
    text, _ = call_llm(
        JUDGE_SYSTEM,
        user,
        json_mode=True,
        model=OPENAI_JUDGE_MODEL,
        temperature=LLM_JUDGE_TEMPERATURE,
    )
    raw = json.loads(text).get("scores") or {}
    missing = [k for k in rubric if k not in raw]
    if missing:
        raise ValueError(f"Judge 가 rubric 항목을 빠뜨렸다: {missing}")
    return {k: int(raw[k]) for k in rubric}          # rubric 순서·범위로 정규화


def run_pilot(items: list[dict], generate, target_item_count: int) -> dict:
    """items: 골든 데이터셋 문항 N건. generate: 문항 → 모델 응답 dict."""
    preflight()
    runs_by_item: dict[str, dict[str, list[int]]] = {}
    details, failures = [], []

    for item in items:
        snap = token_snapshot()
        rubric = item["expected"]["rubric"]

        # ① 생성 1회 — 응답을 고정한다
        #    생성이 실패해도 파일럿을 멈추지 않는다. 채점할 응답이 없을 뿐이고
        #    이건 Judge 안정성과 별개 트랙이다(D-300).
        try:
            response = generate(item)
        except Exception as exc:                     # noqa: BLE001
            runs_by_item[item["id"]] = {}
            failures.append({"id": item["id"], "stage": "generation",
                             "error": f"{type(exc).__name__}: {exc}"})
            details.append({"id": item["id"], "generated": False,
                            "tokens": item_token_delta(snap)})
            continue

        # ② 같은 응답을 3회 채점한다
        try:
            runs = [_judge_once(item["question"], response, rubric)
                    for _ in range(JUDGE_REPEAT)]
        except Exception as exc:                     # noqa: BLE001
            runs_by_item[item["id"]] = {}
            failures.append({"id": item["id"], "stage": "judge",
                             "error": f"{type(exc).__name__}: {exc}"})
            details.append({"id": item["id"], "generated": True, "judged": False,
                            "tokens": item_token_delta(snap)})
            continue

        # ③ 판정용 자료 구조로 옮긴다 — {rubric항목: [1회차, 2회차, 3회차]}
        runs_by_item[item["id"]] = {k: [r[k] for r in runs] for k in rubric}

        details.append({
            "id": item["id"],
            "generated": True,
            "judged": True,
            "runs": runs,
            "avg": round(statistics.mean(sum(r.values()) / len(r) for r in runs), 3),
            "spread": {k: max(r[k] for r in runs) - min(r[k] for r in runs) for k in rubric},
            "response": response,                    # DoD ③ — 원본 응답 보존
            "tokens": item_token_delta(snap),
        })

    # ★ 판정은 여기서 하지 않는다
    stability = evaluate_stability(runs_by_item, target_item_count=target_item_count)

    usage = build_token_usage()
    judged = max(stability["total_responses"], 1)
    per_item_judge = usage["judge_tokens"] / judged / JUDGE_REPEAT

    return {
        "generation_model": OPENAI_MODEL,
        "judge_model": OPENAI_JUDGE_MODEL,
        "judge_temperature": LLM_JUDGE_TEMPERATURE,
        "judge_repeat": JUDGE_REPEAT,
        "judge_prompt_sha": hashlib.sha256(JUDGE_SYSTEM.encode()).hexdigest()[:12],
        "passed": stability["passed"],
        "stability": stability,
        "failures": failures,
        "token_usage": usage,
        "projected_judge_tokens_full_run": round(per_item_judge * target_item_count * 2),
        "items": details,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Judge 재현성 파일럿 (D-276·D-298)")
    ap.add_argument("--area", choices=sorted(_GENERATORS), required=True)
    ap.add_argument("--items", type=int, default=PILOT_ITEM_COUNT)
    args = ap.parse_args(argv)

    if not DATASET.exists():
        print(f"❌ {DATASET} 이 없다.", file=sys.stderr)
        return 1

    dataset = json.loads(DATASET.read_text(encoding="utf-8"))
    area_items = [i for i in dataset if i["area"] == args.area]
    if not area_items:
        print(f"❌ area={args.area} 문항이 없다.", file=sys.stderr)
        return 1

    module_path, func_name, out_path = _GENERATORS[args.area]
    generate = getattr(importlib.import_module(module_path), func_name)

    report = run_pilot(
        area_items[: args.items],
        generate,
        # ★ 하드코딩하지 않는다 — 데이터셋이 늘면 환산 SD 기준도 함께 움직여야 한다
        target_item_count=len(area_items),
    )
    report["area"] = args.area

    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"area                   : {args.area} (본 평가 {len(area_items)}문항)")
    print(f"generation_model       : {report['generation_model']}")
    print(f"judge_model            : {report['judge_model']} (temp={report['judge_temperature']})")
    print(f"judge_prompt_sha       : {report['judge_prompt_sha']}  ← 본 평가와 같아야 한다")
    print(format_report(report["stability"]))
    print()
    print(f"파일럿 judge 토큰      : {report['token_usage']['judge_tokens']:,}")
    print(f"본 평가 예상(전후 2회) : {report['projected_judge_tokens_full_run']:,} 토큰")
    print(f"미귀속 토큰            : {report['token_usage']['unattributed_tokens']:,} (0 이어야 정상)")
    if report["failures"]:
        print(f"실패 문항              : {[f['id'] for f in report['failures']]}")
    print(f"→ {out}")
    print("\n※ 실제 금액은 팀 디스코드 !usage 로 파일럿 전/후 2회 찍어 대조한다(§10.5).")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
