#!/usr/bin/env python
"""
models/shared/eval/pilot_judge_stability.py
— Judge 재현성 파일럿 (D-276)

    uv run python -m models.shared.eval.pilot_judge_stability

★ 왜 "5문항 1회"로는 부족한가
  파일럿의 목적은 점수의 절대값이 아니라 **자[尺]가 흔들리지 않는지** 확인하는 것이다.
  생성과 채점을 매번 새로 돌리면 점수 차이가
    · 생성이 매번 달라서인지 (LLM_TEMPERATURE=0.3)
    · Judge 가 매번 달라서인지
  구분할 수 없다. 기준 문서 §11.2.2 의 "한 번에 하나만 바꾼다"와 같은 논리다.

★ 그래서 이렇게 측정한다
  1) 문항별로 생성을 **1회만** 돌려 응답을 고정한다
  2) 그 고정된 응답을 Judge 에 **3회** 태운다
  3) 3회 점수가 전부 같아야 통과 — rubric 은 1~5 정수 척도라 편차 0 이 정상이다

  편차가 나오면 temperature 또는 rubric 프롬프트 문제다.
  이 상태로 본 평가를 돌리면 "프롬프트 개선으로 +0.5" 를 증명할 수 없다(§1.4).
"""

from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path

from models.shared.config import (
    LLM_JUDGE_TEMPERATURE,
    OPENAI_JUDGE_MODEL,
    OPENAI_MODEL,
)
from models.shared.eval.token_usage import (
    build_token_usage,
    item_token_delta,
    preflight,
    token_snapshot,
)
from models.shared.llm import call_llm

JUDGE_REPEAT = 3
PILOT_ITEM_COUNT = 5

JUDGE_SYSTEM = """너는 광고 카피 평가자다. 주어진 rubric 항목마다 1~5점의 정수를 매긴다.
근거 없이 후하게 주지 않는다. 애매하면 낮은 쪽을 준다.
JSON 만 출력한다: {"scores": {"항목명": 정수, ...}}"""


def _judge_once(question: str, response: dict, rubric: dict[str, str]) -> dict[str, int]:
    """★ 반드시 temperature=0 으로 호출한다 — 이게 이 파일럿의 전부다(D-275)."""
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
    return {k: int(v) for k, v in json.loads(text)["scores"].items()}


def run_pilot(items: list[dict], generate) -> dict:
    """items: 골든 데이터셋 문항 5건. generate: 문항 → 모델 응답 dict."""
    preflight()
    results, unstable = [], []

    for item in items:
        snap = token_snapshot()

        # ① 생성 1회 — 응답을 고정한다
        response = generate(item)

        # ② 같은 응답을 3회 채점한다
        rubric = item["expected"]["rubric"]
        runs = [_judge_once(item["question"], response, rubric) for _ in range(JUDGE_REPEAT)]

        # ③ 항목별 편차 — 정수 척도이므로 0 이어야 정상
        spread = {
            key: max(r[key] for r in runs) - min(r[key] for r in runs)
            for key in rubric
        }
        stable = all(v == 0 for v in spread.values())
        if not stable:
            unstable.append(item["id"])

        results.append({
            "id": item["id"],
            "runs": runs,
            "avg": round(statistics.mean(sum(r.values()) / len(r) for r in runs), 3),
            "spread": spread,
            "stable": stable,
            "tokens": item_token_delta(snap),
        })

    usage = build_token_usage()
    per_item_judge = usage["judge_tokens"] / max(len(items), 1) / JUDGE_REPEAT

    return {
        "generation_model": OPENAI_MODEL,
        "judge_model": OPENAI_JUDGE_MODEL,
        "judge_temperature": LLM_JUDGE_TEMPERATURE,
        "judge_repeat": JUDGE_REPEAT,
        "passed": not unstable,
        "unstable_items": unstable,
        "token_usage": usage,
        # 본 평가 외삽: Judge 대상은 B-25 + C-20 = 45문항, 전후 2회 = 90회 (D-252)
        "projected_judge_tokens_full_run": round(per_item_judge * 45 * 2),
        "items": results,
    }


def main() -> int:
    ds = Path("shared_data/golden_dataset.json")
    if not ds.exists():
        print("❌ shared_data/golden_dataset.json 이 없다.", file=sys.stderr)
        return 1

    items = [i for i in json.loads(ds.read_text(encoding="utf-8"))
             if i["area"] == "basic"][:PILOT_ITEM_COUNT]

    from models.basic.eval.eval_generation import generate_one  # 기본 챗봇 담당 구현

    report = run_pilot(items, generate_one)
    out = Path("models/basic/eval/reports/pilot_judge_stability.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"judge_model            : {report['judge_model']} (temp={report['judge_temperature']})")
    print(f"재현성                 : {'✅ 통과' if report['passed'] else '❌ 실패 ' + str(report['unstable_items'])}")
    print(f"파일럿 judge 토큰      : {report['token_usage']['judge_tokens']:,}")
    print(f"본 평가 예상(45×2회)   : {report['projected_judge_tokens_full_run']:,} 토큰")
    print(f"미귀속 토큰            : {report['token_usage']['unattributed_tokens']:,} (0 이어야 정상)")
    print(f"→ {out}")
    print("\n※ 실제 금액은 팀 디스코드 !usage 로 파일럿 전/후 2회 찍어 대조한다(§10.5).")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
