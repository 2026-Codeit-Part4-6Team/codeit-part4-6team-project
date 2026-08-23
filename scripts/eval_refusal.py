"""
scripts/eval_refusal.py
거부(R-) 골든 데이터셋 60문항 평가 실행기 (관리: 전민재 PM)

    # ① degrade 기준선 — LLM 판정을 끄고 1단 + KB 규칙만으로 측정
    uv run python scripts/eval_refusal.py --rag-disabled \
        --changed "baseline" --out models/shared/eval/reports/refusal_degrade.json

    # ② full RAG — 벡터 검색 + LLM 판정
    uv run python scripts/eval_refusal.py --require-vector \
        --changed "2단 RAG 판정 활성화" --out .../refusal_rag.json

    # ③ 비교
    uv run python -m models.shared.eval.compare_reports \
        .../refusal_degrade.json .../refusal_rag.json --markdown

★ 이 스크립트가 존재하는 이유
  refusal_metrics.py 는 지표를 '계산' 하는 라이브러리이고, 문항 60개를 돌며
  어느 검증 함수를 부를지 분기하고 검색 결과를 모으는 '실행' 은 여기서 한다.

★ preflight 가 맨 앞에 있는 이유
  벡터 인덱스가 안 붙으면 legal_retriever 가 경고 한 줄만 남기고 로컬 검색으로
  조용히 내려간다. 그 상태로 degrade/RAG 를 비교하면 둘 다 같은 경로라
  "차이 없음" 이 나오고 "RAG 가 효과 없다" 는 틀린 결론에 도달한다.
  실제로 numpy 미설치로 이 상황이 발생한 적이 있다.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

KST = timezone(timedelta(hours=9))
DATASET = ROOT / "shared_data" / "golden_refusal.json"
DEFAULT_OUT = ROOT / "models" / "shared" / "eval" / "reports" / "refusal.json"


# ═════════════════════════════════════════════════════════════════════════════
# 1. preflight — 무엇을 측정하는지 확정하고, 기대와 다르면 시작하지 않는다
# ═════════════════════════════════════════════════════════════════════════════
def preflight(*, require_vector: bool, rag_disabled: bool) -> dict:
    """측정 조건을 찍고 검증한다. 반환값은 결과 파일 헤더에 그대로 들어간다."""
    from validation import config as C
    from validation.rag.legal_retriever import chunks, mode

    kb_count = len(chunks())          # KB 가 비면 여기서 LegalKBMissing 이 난다
    actual_mode = mode()
    has_key = C.has_openai_key()

    print("== 측정 조건 ==")
    print(f"  검색 모드       : {actual_mode}")
    print(f"  legal_kb 청크   : {kb_count}")
    print(f"  OPENAI_API_KEY  : {'설정됨' if has_key else '없음'}")
    print(f"  RAG_ENABLED     : {C.RAG_ENABLED}")
    print(f"  judge_model     : {C.JUDGE_MODEL} (temp={C.JUDGE_TEMPERATURE})")
    print(f"  embed_model     : {C.EMBED_MODEL}")
    print(f"  top_k           : {C.RETRIEVE_TOP_K}")

    if require_vector and actual_mode != "vector":
        raise SystemExit(
            f"\n❌ vector 모드를 기대했으나 '{actual_mode}' 이다. 평가를 중단한다.\n"
            "   확인 순서:\n"
            '   1) uv run python -c "import numpy"        ← 맨 python 이 아닌지\n'
            "   2) uv run python scripts/build_legal_index.py\n"
            "   3) legal_kb.md 를 고쳤다면 build_legal_kb.py 부터 다시\n"
            "   RAG 없이 재려면 --rag-disabled 를 명시한다."
        )

    if not rag_disabled and not has_key:
        raise SystemExit(
            "\n❌ OPENAI_API_KEY 가 없는데 --rag-disabled 도 없다.\n"
            "   이대로 돌리면 2단 LLM 판정이 조용히 degrade 되어\n"
            "   '2단을 켠 측정' 과 '끈 측정' 이 같은 결과를 낸다.\n"
            "   의도한 것이라면 --rag-disabled 를 명시한다."
        )

    # ★ 2단이 실제로 도는지 1회 호출해 확인한다.
    #   검색 모드만 검증하면 부족하다 — llm_judge 가 400 을 받으면 degrade 로
    #   내려가 "RAG 를 켠 결과" 가 아니라 degrade 결과가 나온다.
    #   실제로 max_tokens/max_completion_tokens 파라미터 차이 때문에
    #   두 번의 평가가 degrade 결과를 내고도 "RAG" 로 기록됐다.
    judge_ok = None
    if not rag_disabled:
        judge_ok = _smoke_judge()

    return {
        "judge_smoke_passed": judge_ok,
        "retrieval_mode": actual_mode,
        "rag_enabled": (not rag_disabled) and C.RAG_ENABLED,
        "judge_model": C.JUDGE_MODEL,
        "judge_temperature": C.JUDGE_TEMPERATURE,
        "embed_model": C.EMBED_MODEL,
        "retrieve_top_k": C.RETRIEVE_TOP_K,
        "kb_chunk_count": kb_count,
        "kb_source_sha256": _kb_hash(),
    }


def _smoke_judge() -> bool:
    """2단 LLM 판정을 1회 호출해 실제로 도는지 본다.

    ★ llm_judge 의 비공개 이름(_TOKEN_PARAM 등)을 읽지 않는다(D-322).
      구현 세부사항이라 리팩토링하면 사라지고, 그때 이 스크립트가 깨진다.
      실제로 call_llm 경유로 바꾸면서 그 변수들이 없어져 AttributeError 가 났다.

    ★ 대신 **토큰 증가량**을 본다.
      "판정이 돌았는가" 와 "그 사용량이 집계되는가" 는 다른 질문이고,
      둘 다 확인해야 judge 토큰 0 의 원인을 구분할 수 있다.
    """
    from models.shared.llm import get_total_tokens
    from validation.rag import legal_retriever as R
    from validation.rag import llm_judge

    probe = "우리 가게가 최고입니다"
    before = get_total_tokens()
    docs = R.search(probe, k=2)
    result = llm_judge.judge(probe, docs, ["최고"])
    used = get_total_tokens() - before

    if result is None:
        print("  2단 판정 스모크 : ⚠️ None — 일시 장애이거나 RAG_ENABLED=0 이다")
        print("                    이 상태로 측정하면 degrade 결과가 나온다")
        return False

    print(f"  2단 판정 스모크 : ✅ {result.get('verdict')}  (judge 토큰 {used:,})")
    if used == 0:
        print("     ⚠️ 판정은 됐는데 토큰이 0 이다 — call_llm 경유가 아닐 수 있다.")
        print("        결과 파일의 judge_tokens 도 0 으로 찍혀 '2단 미실행' 으로 오독된다.")
    return True


# 사람이 읽는 버전 — 문항 구성을 크게 바꾸면 손으로 올린다(v1 → v2 → …)
DATASET_LABEL = "refusal-v2"


def _dataset_version() -> str:
    """사람이 읽는 라벨 + 파일 내용 해시.

    ★ 라벨만 쓰면 "문항을 고쳤는데 버전 올리는 걸 잊는" 사고가 난다.
      실제로 60 → 67문항으로 늘렸을 때 v1 그대로였다면 compare_reports 가
      "같은 데이터셋인데 item_count 가 다르다" 로 잡아주긴 하지만,
      문항 **내용**만 바뀐 경우(개수 동일)는 아무도 못 잡는다.

    ★ fixture_version(legal_kb-<sha>)과 같은 방식이다 — 일관성.
      해시는 앞 8자만 쓴다. 충돌 확률은 무시할 수준이고 로그가 읽기 쉬워진다.
    """
    digest = hashlib.sha256(DATASET.read_bytes()).hexdigest()[:8]
    return f"{DATASET_LABEL}-{digest}"


def _kb_hash() -> str:
    """legal_kb.md 해시 — 어떤 KB 로 낸 수치인지 나중에 대조할 수 있어야 한다."""
    from validation.rag.legal_retriever import load_kb

    return load_kb().get("source_sha256", "")[:16]


# ═════════════════════════════════════════════════════════════════════════════
# 2. rows 조립 — 문항마다 어느 검증 함수를 부를지 분기한다
# ═════════════════════════════════════════════════════════════════════════════
def evaluate_items(items: list[dict], *, verbose: bool) -> list[dict]:
    from validation.rag import legal_retriever as R
    from validation.regulation import check_regulation, screen
    from validation.security import check_input, check_output
    from validation.self_check import self_check

    kb = R.by_id()
    rows: list[dict] = []

    for idx, item in enumerate(items, 1):
        expected = item["expected"]
        checked_by = expected["checked_by"]
        direct = (item.get("input") or {}).get("direct")
        retrieved: list[str] = []
        started = time.monotonic()

        if checked_by == "check_output":
            verdict = check_output(direct["output_text"])

        elif checked_by == "self_check":
            verdict = self_check(direct.get("result") or {}, direct.get("context") or {})

        elif checked_by == "check_input":
            verdict = check_input(item["question"])

        elif checked_by == "check_regulation":
            verdict = check_regulation(item["question"])
            # 2층(RAGAS) 측정용 — 1단에 걸린 경우에만 검색이 일어난다
            hits = screen(item["question"])
            if hits:
                retrieved = [
                    d["id"] for d in R.search(
                        item["question"], prefer_ids=[h["id"] for h in hits]
                    )
                ]

        else:
            # 과잉 차단 가드 — checked_by 가 배열이다. 두 함수 모두 pass 여야 한다.
            v_in = check_input(item["question"])
            verdict = v_in if v_in["action"] != "pass" else check_regulation(item["question"])

        elapsed = time.monotonic() - started
        row = {
            "item": item,
            "verdict": verdict,
            "gold": expected["action"],
            "pred": verdict.get("action"),
            "retrieved_ids": retrieved,
            "kb_by_id": kb,
            "latency_s": round(elapsed, 3),
        }
        rows.append(row)

        if verbose:
            mark = "✅" if row["gold"] == row["pred"] else "❌"
            print(f"  [{idx:>2}/{len(items)}] {mark} {item['id']} "
                  f"{row['gold']:>6} → {row['pred']:<6} {elapsed:>5.2f}s  "
                  f"{item['question'][:34]}")

    return rows


# ═════════════════════════════════════════════════════════════════════════════
# 3. 요약 조립 — summarize() 를 쓰되 견고성만 선택적으로 끈다
# ═════════════════════════════════════════════════════════════════════════════
def build_summary(rows, items, *, skip_invariance, recheck, verdict_of, kb_by_id, screen_fn):
    """refusal_metrics.summarize() 와 같은 결과를 내되 L4 를 끌 수 있게 한다.

    ★ 견고성이 비용의 3분의 2다 — 문항당 변형 4종 × 54문항 = 216건이고,
      변형된 문자열은 캐시 키가 달라 2단 LLM 을 매번 새로 부른다(최대 +96회).
      1차 실행에서는 끄는 편이 낫다. 불변성은 1단 정규화 문제라 2단을 켜도 안 바뀐다.

    ★ 끌 때는 0.0 이나 1.0 이 아니라 null 을 넣는다.
      "측정 안 함" 과 "만점" 은 다르다 — 0 을 넣으면 실패로, 1 을 넣으면 통과로
      오해된다(D-279 의 unattributed_tokens 와 같은 취지).
    """
    from models.shared.eval import refusal_metrics as M

    head = M.headline_metrics(rows)
    cost = M.safety_cost(rows)
    prf = M.per_class_prf(rows)
    ret = M.retrieval_metrics(rows)
    alt = M.alternative_metrics(rows, recheck)
    cov = M.coverage_metrics(items, kb_by_id, screen_fn)
    inv = None if skip_invariance else M.invariance_metrics(items, verdict_of)

    metrics = {
        "block_recall": head["block_recall"],
        "warn_recall": head["warn_recall"],
        "over_block_rate": head["over_block_rate"],
        "alternative_rate": head["alternative_rate"],
        "alternative_validity": alt["validity_rate"],
        "safety_score": cost["safety_score"],
        "macro_f1": prf["macro_f1"],
        "accuracy": prf["accuracy"],
        "context_recall": ret["context_recall"],
        "context_precision": ret["context_precision"],
        "faithfulness": ret["faithfulness"],
        "ragas_score": ret["ragas_score"],
        "mrr": ret["mrr"],
        "hit_at_1": ret["hit_at_1"],
        "ndcg_at_3": ret["ndcg_at_3"],
        "invariance_rate": inv["invariance_rate"] if inv else None,
        "kb_coverage_rate": cov["kb_coverage_rate"],
        "latency_p50_s": _percentile([r["latency_s"] for r in rows], 50),
        "latency_p95_s": _percentile([r["latency_s"] for r in rows], 95),
    }
    targets = {
        "block_recall": head["block_recall"] >= M.TARGET_BLOCK_RECALL,
        "over_block_rate": head["over_block_rate"] <= M.TARGET_OVER_BLOCK_RATE,
        "alternative_rate": head["alternative_rate"] >= M.TARGET_ALTERNATIVE_RATE,
        "alternative_validity": alt["validity_rate"] >= M.TARGET_ALTERNATIVE_VALIDITY,
        "ragas_score": ret["ragas_score"] >= M.TARGET_RAGAS,
    }
    if inv:
        targets["invariance_rate"] = inv["invariance_rate"] >= M.TARGET_INVARIANCE

    return {
        "metrics": metrics,
        "targets_met": targets,
        "detail": {
            "headline": head, "safety_cost": cost, "per_class": prf,
            "confusion_matrix": M.confusion_matrix(rows), "retrieval": ret,
            "alternative": alt, "coverage": cov,
            "invariance": inv or {"skipped": True},
        },
    }


def _percentile(values: list[float], pct: int) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = min(int(len(ordered) * pct / 100), len(ordered) - 1)
    return round(ordered[idx], 3)


# ═════════════════════════════════════════════════════════════════════════════
# 4. 결과 파일 — compare_reports 가 읽을 수 있는 헤더를 갖춘다
# ═════════════════════════════════════════════════════════════════════════════
def build_report(summary: dict, rows: list[dict], conditions: dict,
                 *, changed: str, skip_invariance: bool) -> dict:

    return {
        # ── compare_reports._CONDITIONS 5필드 (D-279) ──────────────────────
        #    R- 는 생성을 하지 않으므로 generation_model 은 판정 모델과 같게 둔다.
        "run_at": datetime.now(KST).isoformat(timespec="seconds"),
        "area": "refusal",
        "generation_model": conditions["judge_model"],
        "judge_model": conditions["judge_model"],
        "dataset_version": _dataset_version(),
        "fixture_version": f"legal_kb-{conditions['kb_source_sha256']}",
        "trend_fixture_version": "n/a",
        # ── R- 전용 조건 ──────────────────────────────────────────────────
        "retrieval_mode": conditions["retrieval_mode"],
        "rag_enabled": conditions["rag_enabled"],
        "judge_temperature": conditions["judge_temperature"],
        "embed_model": conditions["embed_model"],
        "retrieve_top_k": conditions["retrieve_top_k"],
        "kb_chunk_count": conditions["kb_chunk_count"],
        "judge_smoke_passed": conditions.get("judge_smoke_passed"),
        "invariance_measured": not skip_invariance,
        "item_count": len(rows),
        "changed": changed,
        "token_usage": _token_usage(),
        "metrics": summary["metrics"],
        "targets_met": summary["targets_met"],
        "detail": summary["detail"],
        "items": [
            {
                "id": r["item"]["id"],
                "type": r["item"]["type"],
                "expected": r["gold"],
                "actual": r["pred"],
                "passed": r["gold"] == r["pred"],
                "law": r["verdict"].get("law", ""),
                "alternative": r["verdict"].get("alternative", ""),
                "retrieved_ids": r["retrieved_ids"],
                "latency_s": r["latency_s"],
            }
            for r in rows
        ],
    }


def _token_usage() -> dict:
    """모델별 원본 집계에서 파생시킨다(D-278). judge 만 쓰므로 단순하다."""
    from models.shared.llm import get_total_tokens
    from validation import config as C

    return {
        "by_model": {C.JUDGE_MODEL: get_total_tokens(C.JUDGE_MODEL)},
        "judge_tokens": get_total_tokens(C.JUDGE_MODEL),
        "total_tokens": get_total_tokens(),
        "unattributed_tokens": get_total_tokens() - get_total_tokens(C.JUDGE_MODEL),
    }


# ═════════════════════════════════════════════════════════════════════════════
def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="거부(R-) 골든 데이터셋 평가")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--rag-disabled", action="store_true",
                    help="2단 LLM 판정을 끈다. degrade 기준선 측정용")
    ap.add_argument("--require-vector", action="store_true",
                    help="검색 모드가 vector 가 아니면 중단한다")
    ap.add_argument("--skip-invariance", action="store_true",
                    help="견고성(L4) 측정을 건너뛴다. 비용의 3분의 2를 아낀다")
    ap.add_argument("--changed", default="", help='§11.1 "바꾼 것" 한 줄 (D-261)')
    ap.add_argument("--check-only", action="store_true",
                    help="측정 조건만 확인하고 평가는 하지 않는다")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args(argv)

    if args.rag_disabled:
        os.environ["VALIDATION_RAG_ENABLED"] = "0"     # config 를 import 하기 전에 설정

    if not DATASET.exists():
        print(f"❌ {DATASET} 이 없다. build_golden_refusal.py 를 먼저 실행하라.",
              file=sys.stderr)
        return 1

    conditions = preflight(require_vector=args.require_vector,
                           rag_disabled=args.rag_disabled)

    if args.check_only:
        print("\n✅ 측정 조건 확인 완료 (--check-only 이므로 평가는 하지 않는다)")
        return 0

    from models.shared.llm import reset_total_tokens
    from validation.rag import legal_retriever as R
    from validation.regulation import check_regulation, screen
    from validation.security import check_input

    reset_total_tokens()                # 이전 실행 잔재를 비운다(D-267)

    items = json.loads(DATASET.read_text(encoding="utf-8"))
    print(f"\n== 평가 시작 ({len(items)}문항) ==")
    started = time.monotonic()
    rows = evaluate_items(items, verbose=not args.quiet)

    def verdict_of(text: str) -> str:
        v = check_input(text)
        return v["action"] if v["action"] != "pass" else check_regulation(text)["action"]

    summary = build_summary(
        rows, items,
        skip_invariance=args.skip_invariance,
        recheck=check_regulation, verdict_of=verdict_of,
        kb_by_id=R.by_id(), screen_fn=screen,
    )
    report = build_report(summary, rows, conditions,
                          changed=args.changed, skip_invariance=args.skip_invariance)

    print(render(summary, skip_invariance=args.skip_invariance))

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    elapsed = time.monotonic() - started
    tok = report["token_usage"]
    print(f"\n  소요 {elapsed:.1f}초 / judge 토큰 {tok['judge_tokens']:,}")
    if args.skip_invariance:
        print("  ⚠️ 견고성(L4)은 측정하지 않았다 — invariance_rate 는 null 이다")
    print(f"  → {args.out}")

    failed = [k for k, ok in summary["targets_met"].items() if not ok]
    if failed:
        print(f"\n  ❌ 목표 미달: {failed}")
    return 0


def render(summary: dict, *, skip_invariance: bool) -> str:
    """화면 리포트.

    refusal_metrics.format_report() 를 쓰지 않고 여기서 직접 그린다 —
    그쪽은 invariance_rate 가 항상 숫자라고 가정해 None 을 넣으면 TypeError 가 난다.
    "측정 안 함" 을 표현하려면 출력도 그 상태를 알아야 한다.
    """
    m, t, d = summary["metrics"], summary["targets_met"], summary["detail"]

    def ok(key: str) -> str:
        return "✅" if t.get(key) else "❌"

    cm = d["confusion_matrix"]
    actions = ("block", "warn", "pass", "reject")
    L = ["", "== 거부(R-) 영역 평가 ==", "", "  [L1] 판정 정확도"]
    L.append("        예측→ " + "".join(f"{a:>8}" for a in actions))
    for gold in actions:
        L.append(f"   정답 {gold:<6}" + "".join(f"{cm[gold][p]:>8}" for p in actions))
    L += [
        f"    {ok('block_recall')} 차단 정확도   {m['block_recall']:.1%}  (목표 100%)",
        f"    {ok('over_block_rate')} 과잉 차단률   {m['over_block_rate']:.1%}  (목표 10% 이하)",
        f"       Macro-F1      {m['macro_f1']:.3f}   Accuracy {m['accuracy']:.3f}",
        (f"       안전 점수      {m['safety_score']:.3f}   "
         f"(누락 {d['safety_cost']['miss']}건, 과잉 {d['safety_cost']['over_block']}건)"),
        "",
        f"  [L2] 검색 품질 ({d['retrieval']['measured_items']}문항)",
        (f"       recall {m['context_recall']:.3f}   "
         f"precision {m['context_precision']:.3f}   "
         f"faithfulness {m['faithfulness']:.3f}"),
        f"    {ok('ragas_score')} RAGAS 종합     {m['ragas_score']:.3f}  (조화평균, 목표 0.80)",
        f"       MRR {m['mrr']:.3f}   Hit@1 {m['hit_at_1']:.3f}   nDCG@3 {m['ndcg_at_3']:.3f}",
        "",
        "  [L3] 대안 품질",
        f"    {ok('alternative_rate')} 대안 제시율   {m['alternative_rate']:.1%}",
        f"    {ok('alternative_validity')} ★대안 유효성  {m['alternative_validity']:.1%}",
        f"       대안 다양성    {d['alternative']['distinct_rate']:.1%}",
        "",
        "  [L4] 견고성",
    ]
    if skip_invariance:
        L.append("       측정하지 않음 (--skip-invariance)")
    else:
        inv = d["invariance"]
        L += [(f"    {ok('invariance_rate')} 불변성        {m['invariance_rate']:.1%}  "
               f"({inv['tested']}건 중 {inv['flipped']}건 뒤집힘)"),
              f"       유형별: {inv['by_perturbation']}"]
    L += ["", "  [L5] 커버리지",
          (f"       legal_kb  {d['coverage']['kb_covered']}/{d['coverage']['kb_total']} "
           f"= {m['kb_coverage_rate']:.1%}"),
          (f"       트리거    {d['coverage']['trigger_fired']}/"
           f"{d['coverage']['trigger_total']} "
           f"= {d['coverage']['trigger_coverage_rate']:.1%}"),
          "", f"       응답시간   p50 {m['latency_p50_s']:.3f}s   p95 {m['latency_p95_s']:.3f}s"]

    h, a, c = d["headline"], d["alternative"], d["coverage"]
    if h["missed_ids"]:
        L.append(f"\n  ⚠️ 놓친 차단: {h['missed_ids']}")
    if h["over_blocked_ids"]:
        L.append(f"  ⚠️ 과잉 차단: {h['over_blocked_ids']}")
    if a["invalid"]:
        L.append(f"  ⚠️ 다시 걸리는 대안: {[i['id'] for i in a['invalid']]}")
    if c["uncovered_kb_ids"]:
        L.append(f"  ⚠️ 미검증 조문: {c['uncovered_kb_ids']}")
    return "\n".join(L)


if __name__ == "__main__":
    raise SystemExit(main())
