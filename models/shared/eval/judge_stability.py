"""
models/shared/eval/judge_stability.py
— Judge 안정성 판정 (D-298: D-276 의 '편차 0' 기준을 대체한다)

★ 왜 '편차 0' 을 버리는가
  temperature=0 은 결정론을 보장하지 않는다. 배치 구성에 따라 GPU 축약 순서가
  바뀌면 로짓 하위 자릿수가 흔들리고, 두 등급의 점수가 비슷할 때 argmax 가 뒤집힌다.
  즉 '편차 0' 은 API 기반 LLM Judge 가 원리적으로 만족할 수 없는 기준이었다.
  기준을 못 맞춰서 본 평가를 못 돌리면, 기준이 평가를 막은 셈이 된다.

★ 그래도 목적은 그대로다
  D-276 의 목적은 "자[尺]가 흔들리면 +0.5 개선을 증명할 수 없다" 였다.
  → 절대 결정론이 아니라 **노이즈가 재려는 효과보다 충분히 작은가**로 바꾼다.

★ 3계층 판정
  ① 셀(문항×rubric)  : max-min <= 1   — 인접 등급 흔들림은 허용, 2 이상은 실패
                                        (2 이상은 rubric 문구가 모호하다는 신호)
  ② 문항(rubric 평균) : max-min <= 0.5 — 여러 항목이 동시에 흔들린 경우를 잡는다
  ③ 데이터셋          : llm_judge_avg 재현 SD <= 0.05  ← ★ 진짜 통과 기준
                                        비교표에 싣는 숫자가 이것이기 때문이다
"""

from __future__ import annotations

import statistics

CELL_MAX_SPREAD = 1.0        # ① 인접 등급까지 허용
ITEM_MAX_SPREAD = 0.5        # ②
DATASET_MAX_SD = 0.05        # ③
MDE_SIGMA = 3.0              # 최소 검출 가능 효과 = 두 측정 차이의 3σ


def evaluate_stability(runs_by_item: dict[str, dict[str, list[int]]],
                       target_item_count: int) -> dict:
    """runs_by_item: {문항ID: {rubric항목: [1회차, 2회차, 3회차]}}

    target_item_count: 본 평가 문항 수(컨설턴트 60 / 기본 25).
        파일럿 표본에서 관측한 흔들림 비율을 본 평가 규모로 외삽한다.
    """
    cells, cell_fail, item_fail = [], [], []

    for item_id, rubric in runs_by_item.items():
        if not rubric:                       # 생성 실패 문항 — 채점할 응답이 없다
            continue
        for name, scores in rubric.items():
            spread = max(scores) - min(scores)
            cells.append(spread)
            if spread > CELL_MAX_SPREAD:
                cell_fail.append(f"{item_id}·{name} {scores} (편차 {spread})")

        runs = len(next(iter(rubric.values())))
        per_run_avg = [
            statistics.mean(scores[i] for scores in rubric.values()) for i in range(runs)
        ]
        item_spread = max(per_run_avg) - min(per_run_avg)
        if item_spread > ITEM_MAX_SPREAD:
            item_fail.append(f"{item_id} 평균 {per_run_avg} (편차 {item_spread:.2f})")

    flip_rate = sum(1 for s in cells if s > 0) / len(cells) if cells else 0.0
    rubric_k = max((len(r) for r in runs_by_item.values() if r), default=4)

    # 흔들리는 셀은 두 등급 사이를 오간다 → 셀당 분산 상한 p(1-p) = 0.25
    # 전체 셀 평균의 표준오차 = sqrt(flip_rate * 0.25 / 총셀수)
    n_cells = target_item_count * rubric_k
    projected_sd = (flip_rate * 0.25 / n_cells) ** 0.5
    mde = MDE_SIGMA * (2 ** 0.5) * projected_sd      # 두 측정 차이의 3σ

    passed = not cell_fail and not item_fail and projected_sd <= DATASET_MAX_SD
    return {
        "passed": passed,
        "measured_cells": len(cells),
        "flip_rate": round(flip_rate, 4),
        "cells_over_1": cell_fail,
        "items_over_0_5": item_fail,
        "projected_dataset_sd": round(projected_sd, 4),
        "dataset_sd_limit": DATASET_MAX_SD,
        "minimum_detectable_effect": round(mde, 3),
        "target_item_count": target_item_count,
    }


def format_report(result: dict) -> str:
    ok = "✅ 통과" if result["passed"] else "❌ 실패"
    lines = [
        f"Judge 안정성 판정: {ok}",
        f"  측정 셀            : {result['measured_cells']}개",
        f"  흔들린 비율        : {result['flip_rate']:.0%}",
        f"  ① 편차 2 이상 셀   : {len(result['cells_over_1'])}건",
        f"  ② 문항 평균 편차   : {len(result['items_over_0_5'])}건 초과",
        f"  ③ 본 평가 {result['target_item_count']}문항 환산 SD : "
        f"{result['projected_dataset_sd']:.4f} (기준 {result['dataset_sd_limit']})",
        f"  최소 검출 가능 효과: ±{result['minimum_detectable_effect']:.2f} "
        f"— 이보다 작은 변화는 개선이라 부르지 않는다",
    ]
    for f in result["cells_over_1"] + result["items_over_0_5"]:
        lines.append(f"    · {f}")
    return "\n".join(lines)


# ═════════════════════════════════════════════════════════════════════════════
# 앵커 문항 — Judge 자체가 시간에 따라 움직였는지 검출한다 (D-302)
# ═════════════════════════════════════════════════════════════════════════════
ANCHOR_MAX_DRIFT = 0.25


def check_anchor_drift(before: dict[str, dict[str, int]],
                       after: dict[str, dict[str, int]]) -> dict:
    """튜닝 전 측정에서 저장한 응답을, 튜닝 후 측정 때 **그대로 다시 채점**한 결과를 비교한다.

    응답이 동일하므로 점수도 같아야 한다. 달라졌다면 모델이 개선된 게 아니라
    **자[尺]가 움직인 것**이다. 이 경우 튜닝 전후 비교는 그만큼 신뢰할 수 없다.
    비용은 문항 3건 재채점이라 무시할 수준이다.
    """
    drifts, detail = [], []
    for item_id in sorted(set(before) & set(after)):
        b, a = before[item_id], after[item_id]
        db = statistics.mean(b.values())
        da = statistics.mean(a.values())
        drifts.append(da - db)
        detail.append({"id": item_id, "before": round(db, 3), "after": round(da, 3),
                       "drift": round(da - db, 3)})
    mean_drift = statistics.mean(drifts) if drifts else 0.0
    return {
        "anchor_count": len(drifts),
        "mean_drift": round(mean_drift, 3),
        "within_tolerance": abs(mean_drift) <= ANCHOR_MAX_DRIFT,
        "tolerance": ANCHOR_MAX_DRIFT,
        "items": detail,
        "note": ("자[尺] 이동 없음 — 비교 유효"
                 if abs(mean_drift) <= ANCHOR_MAX_DRIFT
                 else f"Judge 가 평균 {mean_drift:+.2f} 이동했다 — 비교표에 이 값을 함께 기록한다"),
    }
