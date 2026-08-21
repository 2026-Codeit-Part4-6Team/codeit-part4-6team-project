"""
models/shared/eval/compare_reports.py
— 두 결과 파일이 비교 가능한 조건인지 확인한다 (기준 문서 §11.2 · D-262)

발표 자료를 만들기 전에 돌린다 — 조건이 둘 이상 다른 표는 아무것도 증명하지
못하므로, 사람이 눈으로 대조하는 대신 기계가 막는다.

    # 1차 측정 직후 — 결과 파일 형식만 검사 (비교 상대가 아직 없을 때)
    uv run python -m models.shared.eval.compare_reports --validate \
        models/basic/eval/reports/2026-08-21.json

    # 튜닝 후 — 비교 가능성 확인 + 발표용 표 생성
    uv run python -m models.shared.eval.compare_reports \
        models/basic/eval/reports/2026-08-21.json \
        models/basic/eval/reports/2026-08-22.json --markdown

★ 문서 §11.2 초안에서 보완한 것 (D-281)
  ① 헤더 필드가 **양쪽 다 없으면** before.get()==after.get()==None 이라
     "조건이 하나도 안 바뀌었다"로 판정된다 → 필수 필드 존재를 먼저 검증한다
  ② area 를 보지 않아 basic 결과와 consult 결과를 비교해도 통과한다
  ③ item_count 를 보지 않아 한쪽이 문항을 빠뜨려도 통과한다 (§10.4 DoD ①)
  ④ judge_temperature 를 보지 않아 자[尺]가 흔들린 측정도 통과한다 (D-275)
  ⑤ __main__ 블록이 없어 문서에 적힌 실행 명령이 아무것도 출력하지 않는다

★ 반환 계약은 초안 그대로 유지한다
  comparable · means · changed · reason 네 키는 이름과 의미를 바꾸지 않는다.
  문서를 읽고 온 담당자가 다른 코드를 만나면 안 된다(D-263).
"""

from __future__ import annotations

import argparse
import json
import sys
import unicodedata
from pathlib import Path

# ── 한 번에 하나만 바뀌어야 비교가 성립하는 조건들 (§11.2.1) ──────────────────
# ⚠️ models/shared/eval/token_usage.py 의 CONDITION_FIELDS 와 반드시 같아야 한다.
#    한쪽만 늘리면 결과 파일에 없는 필드를 비교하게 되어 ① 결함이 재발한다.
_CONDITIONS = (
    "generation_model",
    "judge_model",
    "dataset_version",
    "fixture_version",
    "trend_fixture_version",
)

# 이 조건은 단독으로 달라도 비교가 성립한다(§11.2.1)
_COMPARABLE_ALONE = {
    "generation_model": "생성 모델 성능 차이",
    "judge_model": "채점자 성향 차이",
    "fixture_version": "입력 데이터 정확도 개선 효과",
}

# 비교 가능하지만 해석에 단서가 붙는 경우
_CAVEAT = {
    "judge_model": (
        "Judge 자체 검증용 비교다. 본 평가 baseline 으로 쓰지 않는다 — "
        "judge_model 변경 시 그때까지 낸 점수는 전량 폐기 대상이다(D-258·§11.4)."
    ),
}

# 결과 파일에 반드시 있어야 하는 헤더 (§10.4 DoD ⑤ · D-263)
_REQUIRED = _CONDITIONS + ("run_at", "area", "item_count", "metrics")

# 낮을수록 좋은 지표 — 화살표 방향이 뒤집힌다(§11.1 표)
_LOWER_IS_BETTER = {
    "hallucination_rate",
    "failure_rate",
    "over_block_rate",
    "latency_p50_s",
    "latency_p95_s",
}
_PERCENT_METRICS = {
    "hallucination_rate",
    "failure_rate",
    "over_block_rate",
    "contract_compliance",
    "trend_path_match_rate",
    "block_recall",
    "alternative_rate",
}


class ReportFormatError(ValueError):
    """결과 파일이 비교에 쓸 수 없는 형식이다."""


# ═════════════════════════════════════════════════════════════════════════════
# 1) 검증 — 1차 측정 직후에 단독으로 돌린다
# ═════════════════════════════════════════════════════════════════════════════
def validate_report(report: dict, label: str = "") -> list[str]:
    """결과 파일 하나의 형식 문제를 목록으로 반환한다. 빈 리스트면 정상.

    ★ 1차 측정 직후 바로 돌리는 것이 핵심이다.
      8/22 에 비교하려다 8/21 결과에 judge_model 이 없는 걸 알면
      baseline 을 다시 측정해야 하고, 그만큼 $30 예산이 또 나간다.
    """
    tag = f"[{label}] " if label else ""
    problems: list[str] = []

    for key in _REQUIRED:
        if key not in report:
            problems.append(f"{tag}필수 헤더 누락: {key} (§10.4 DoD ⑤)")
        elif report[key] in (None, "", {}):
            problems.append(f"{tag}헤더가 비어 있음: {key}={report[key]!r}")

    # ④ 자[尺]가 흔들린 측정은 비교 이전에 무효다
    jt = report.get("judge_temperature")
    if jt is None:
        problems.append(f"{tag}judge_temperature 미기록 — 재현성을 확인할 수 없다(D-275)")
    elif jt != 0:
        problems.append(
            f"{tag}judge_temperature={jt} — 0 이 아니면 같은 응답도 점수가 달라진다(§1.4·D-275)"
        )

    # ③ 모수 일치 확인
    items = report.get("items")
    if isinstance(items, list) and report.get("item_count") not in (None, len(items)):
        problems.append(
            f"{tag}item_count={report['item_count']} 인데 items 는 {len(items)}건 (§10.4 DoD ①)"
        )

    # 토큰 귀속 확인 (D-278)
    usage = report.get("token_usage") or {}
    unattributed = usage.get("unattributed_tokens")
    if unattributed:
        problems.append(
            f"{tag}unattributed_tokens={unattributed} — 계획에 없던 모델 호출이 섞였다(D-278)"
        )
    if report.get("area") == "refusal" and usage.get("judge_tokens"):
        problems.append(
            f"{tag}거부 영역인데 judge_tokens={usage['judge_tokens']} (R- 는 LLM 0회, D-277)"
        )

    return problems


# ═════════════════════════════════════════════════════════════════════════════
# 2) 비교 — 반환 계약은 문서 §11.2 초안 그대로
# ═════════════════════════════════════════════════════════════════════════════
def _load(path: str) -> dict:
    p = Path(path)
    if not p.exists():
        raise ReportFormatError(f"결과 파일이 없다: {path}")
    return json.loads(p.read_text(encoding="utf-8"))


def _metrics_delta(before: dict, after: dict) -> list[dict]:
    """§11.1 비교표 행을 만든다. 공통으로 존재하는 숫자 지표만 다룬다."""
    mb, ma = before.get("metrics") or {}, after.get("metrics") or {}
    rows = []
    for key in mb:
        if key not in ma or not isinstance(mb[key], (int, float)) or not isinstance(ma[key], (int, float)):
            continue
        diff = ma[key] - mb[key]
        improved = diff < 0 if key in _LOWER_IS_BETTER else diff > 0
        # 비율(0~1)로 저장된 지표는 §11 표 형식(88% → 100% → +12%p)으로 보여준다.
        # 0.88 을 그대로 슬라이드에 올리면 읽는 사람이 매번 환산해야 한다.
        is_ratio = key in _PERCENT_METRICS and abs(mb[key]) <= 1 and abs(ma[key]) <= 1
        scale = 100 if is_ratio else 1
        rows.append({
            "metric": key,
            "before": round(mb[key] * scale, 2),
            "after": round(ma[key] * scale, 2),
            "delta": round(diff * scale, 2),
            "improved": improved if diff else None,   # 변화 없으면 None
            "unit": "%p" if is_ratio else "",
            "value_unit": "%" if is_ratio else "",
        })
    only_after = sorted(set(ma) - set(mb))
    if only_after:
        rows.append({"metric": f"(after 에만 있는 지표: {', '.join(only_after)})",
                     "before": None, "after": None, "delta": None,
                     "improved": None, "unit": ""})
    return rows


def compare_reports(before_path: str, after_path: str) -> dict:
    """두 결과 파일의 비교 가능 여부와 그 비교의 의미를 반환한다."""
    before, after = _load(before_path), _load(after_path)

    # ── 게이트 0: 형식 검증 — 초안 ① 결함 차단 ──────────────────────────────
    problems = validate_report(before, "before") + validate_report(after, "after")
    if problems:
        return {
            "comparable": False,
            "means": None,
            "changed": [],
            "reason": "결과 파일 형식이 비교 요건을 충족하지 않는다 — 아래 문제를 먼저 고친다",
            "problems": problems,
            "warnings": [],
            "metrics_delta": [],
        }

    # ── 게이트 1: 같은 영역인가 — 초안 ② 결함 차단 ─────────────────────────
    if before["area"] != after["area"]:
        return {
            "comparable": False,
            "means": None,
            "changed": ["area"],
            "reason": (
                f"area 가 다르다({before['area']} → {after['area']}) — "
                "문항 자체가 다르므로 비교 대상이 아니다"
            ),
            "problems": [],
            "warnings": [],
            "metrics_delta": [],
        }

    # ── 게이트 2: 조건 변경 — 초안 로직 유지 ────────────────────────────────
    changed = [key for key in _CONDITIONS if before.get(key) != after.get(key)]

    # ── 게이트 3: 모수 일치 — 초안 ③ 결함 차단 ─────────────────────────────
    # dataset_version 이 같은데 문항 수가 다르면 한쪽이 측정을 빠뜨린 것이다.
    if "dataset_version" not in changed and before["item_count"] != after["item_count"]:
        return {
            "comparable": False,
            "means": None,
            "changed": changed + ["item_count"],
            "reason": (
                f"dataset_version 은 같은데 item_count 가 다르다"
                f"({before['item_count']} → {after['item_count']}) — "
                "한쪽이 문항을 빠뜨렸다. 재측정한다(§10.4 DoD ①)"
            ),
            "problems": [],
            "warnings": [],
            "metrics_delta": [],
        }

    delta = _metrics_delta(before, after)

    if not changed:
        return {
            "comparable": True,
            "means": "프롬프트 튜닝 효과",
            "changed": [],
            "reason": "",
            "problems": [],
            "warnings": _changed_note_warning(after),
            "metrics_delta": delta,
        }

    if len(changed) == 1 and changed[0] in _COMPARABLE_ALONE:
        warnings = _changed_note_warning(after)
        if changed[0] in _CAVEAT:
            warnings.append(_CAVEAT[changed[0]])
        return {
            "comparable": True,
            "means": _COMPARABLE_ALONE[changed[0]],
            "changed": changed,
            "reason": "",
            "problems": [],
            "warnings": warnings,
            "metrics_delta": delta,
        }

    return {
        "comparable": False,
        "means": None,
        "changed": changed,
        "reason": (
            f"조건 {changed} 가 동시에 달라 원인을 분리할 수 없다 — "
            f"한 번에 하나만 바꿔 재측정한다(§11.2)"
        ),
        "problems": [],
        "warnings": [],
        "metrics_delta": [],
    }


def _changed_note_warning(after: dict) -> list[str]:
    """§11.1 '바꾼 것' 한 줄이 비어 있으면 경고한다(D-261)."""
    if not (after.get("changed") or "").strip():
        return ['"바꾼 것" 한 줄(changed 필드)이 비어 있다 — 숫자만 있으면 우연으로 읽힌다(D-261)']
    return []


# ═════════════════════════════════════════════════════════════════════════════
# 3) 발표용 표 — §11.1 형식 그대로 뽑는다
# ═════════════════════════════════════════════════════════════════════════════
def _display_width(text: str) -> int:
    """전각 문자를 2칸으로 세어 '측정 조건' 블록 정렬을 맞춘다."""
    return sum(2 if unicodedata.east_asian_width(c) in "WF" else 1 for c in text)


def _pad(text: str, width: int) -> str:
    return text + " " * max(0, width - _display_width(text))


def render_markdown(result: dict, before_path: str, after_path: str) -> str:
    """§11 결과 기록 형식 그대로 출력한다. 복사해서 슬라이드에 붙인다."""
    before, after = _load(before_path), _load(after_path)
    lines = [f"### {after['area']} 튜닝 전후 비교", "",
             "| 지표 | 튜닝 전 | 튜닝 후 | 변화 |", "| --- | --- | --- | --- |"]

    for row in result["metrics_delta"]:
        if row["before"] is None:
            lines.append(f"| {row['metric']} | — | — | — |")
            continue
        mark = "" if row["improved"] is None else ("**" if row["improved"] else "")
        sign = "+" if row["delta"] > 0 else ""
        vu = row.get("value_unit", "")
        lines.append(
            f"| {mark}{row['metric']}{mark} | {row['before']}{vu} | {row['after']}{vu} | "
            f"{mark}{sign}{row['delta']}{row['unit']}{mark} |"
        )

    lines += ["", "```", "측정 조건"]
    labels = list(_CONDITIONS) + ["바꾼 것"]
    width = max(_display_width(x) for x in labels)
    for cond in _CONDITIONS:
        same = before.get(cond) == after.get(cond)
        note = "(전·후 동일)" if same else f"(전: {before.get(cond)} → 후: {after.get(cond)})"
        lines.append(f"- {_pad(cond, width)} : {after.get(cond)}  {note}")
    lines.append(f"- {_pad('바꾼 것', width)} : {after.get('changed') or '(미기재)'}")
    lines.append("```")

    if result["warnings"]:
        lines += ["", "> ⚠️ " + "\n> ⚠️ ".join(result["warnings"])]
    return "\n".join(lines)


# ═════════════════════════════════════════════════════════════════════════════
# 4) CLI — 초안 ⑤ 결함 차단
# ═════════════════════════════════════════════════════════════════════════════
def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="결과 파일 비교 가능성 확인 (§11.2)")
    ap.add_argument("paths", nargs="+", help="검증: 파일 1개 / 비교: before after")
    ap.add_argument("--validate", action="store_true", help="형식 검증만 수행")
    ap.add_argument("--markdown", action="store_true", help="§11.1 비교표를 함께 출력")
    ap.add_argument("--json", action="store_true", help="판정 결과를 JSON 으로 출력")
    args = ap.parse_args(argv)

    try:
        if args.validate or len(args.paths) == 1:
            failed = False
            for path in args.paths:
                problems = validate_report(_load(path), Path(path).name)
                if problems:
                    failed = True
                    print(f"❌ {path}")
                    for p in problems:
                        print(f"   · {p}")
                else:
                    print(f"✅ {path} — 헤더 형식 정상")
            return 1 if failed else 0

        if len(args.paths) != 2:
            print("❌ 비교는 before after 두 개만 받는다.", file=sys.stderr)
            return 2

        before_path, after_path = args.paths
        result = compare_reports(before_path, after_path)

        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        elif result["comparable"]:
            print(f"✅ 비교 가능 — {result['means']}")
            if result["changed"]:
                print(f"   달라진 조건: {result['changed']}")
            for w in result["warnings"]:
                print(f"   ⚠️  {w}")
        else:
            print(f"❌ 비교 불가 — {result['reason']}")
            for p in result["problems"]:
                print(f"   · {p}")

        if args.markdown and result["comparable"]:
            print()
            print(render_markdown(result, before_path, after_path))

        return 0 if result["comparable"] else 1

    except ReportFormatError as e:
        print(f"❌ {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
