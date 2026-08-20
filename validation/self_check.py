"""
validation/self_check.py
답변 품질 검증 — 근거 유무·완결성·개수를 규칙으로 판정한다.

반환 규격 (계약서 §5.3)
    action  : "pass" | "warn" | "reject"     ★ block 이 아니라 reject 다
    reasons : list[str]                       실패 사유 목록. pass 면 []
    message : str                             사용자 안내. pass 면 ""

★ (A) 규칙 기반만 구현한다. LLM 호출 0회.
  (B) LLM 사실성 검증은 V-05 [SHOULD] — 예산 여유 있을 때.
  품질 검사에 LLM 을 부르면, 재생성 루프(최대 2회)와 곱해져 호출이 3배가 된다.

★ 두 챗봇의 result 스키마가 다르므로 형태를 보고 분기한다.
  기본 챗봇   : {"proposals"|"ranked_copies": [{"copy":..., "error":...}]}
  컨설턴트    : {"summary":..., "actions":[...], "reasons":[...]}
  시그니처를 바꿀 수 없으므로(계약서 §4 고정) 덕 타이핑이 유일한 방법이다.
"""

from __future__ import annotations

import re

from . import config as C

_WS = re.compile(r"\s+")


def _result(action: str, reasons: list[str] | None = None, message: str = "") -> dict:
    return {"action": action, "reasons": reasons or [], "message": message}


def _norm(s: str) -> str:
    return _WS.sub("", (s or "")).lower()


def _msg(reasons: list[str]) -> str:
    return f"생성 결과에 {reasons[0]} 문제가 있습니다." if reasons else ""


# ═════════════════════════════════════════════════════════════════════════════
# 기본 챗봇 — 카피 3안
# ═════════════════════════════════════════════════════════════════════════════
def _check_proposals(items: list) -> dict:
    alive = [i for i in items if isinstance(i, dict) and (i.get("copy") or "").strip()]

    if not alive:
        return _result(
            "reject",
            ["생성된 카피 없음"],
            "광고 문구를 만들지 못했습니다. 잠시 후 다시 시도해 주세요.",
        )

    reasons: list[str] = []
    if len(alive) < C.EXPECTED_PROPOSALS:
        reasons.append(f"제안 개수 부족({len(alive)}/{C.EXPECTED_PROPOSALS})")

    if any(len((i["copy"]).strip()) < C.MIN_COPY_LEN for i in alive):
        reasons.append("카피 길이 미달")

    # 3안이 사실상 같은 문구면 "3안을 준다"는 약속이 지켜지지 않은 것이다
    if len(alive) > 1 and len({_norm(i["copy"]) for i in alive}) < len(alive):
        reasons.append("카피 중복")

    if reasons:
        return _result("warn", reasons, _msg(reasons))
    return _result("pass")


# ═════════════════════════════════════════════════════════════════════════════
# 컨설턴트 — summary / actions / reasons
# ═════════════════════════════════════════════════════════════════════════════
def _check_strategy(result: dict, context: dict) -> dict:
    summary = (result.get("summary") or "").strip()
    actions = [a for a in (result.get("actions") or []) if _action_text(a)]
    grounds = [r for r in (result.get("reasons") or []) if str(r).strip()]
    sources = context.get("sources") or result.get("sources") or []

    # ── reject: 되돌려야 하는 수준 ───────────────────────────────────────────
    hard: list[str] = []
    if not summary:
        hard.append("요약 없음")
    if not actions:
        hard.append("실행 제안 없음")
    if not grounds and not sources:
        hard.append("답변 근거 없음")
    if hard:
        return _result("reject", hard, "생성 결과에 답변 근거가 부족합니다.")

    # ── warn: 약하지만 보여줘도 되는 수준 ───────────────────────────────────
    soft: list[str] = []
    if len(summary) < C.MIN_SUMMARY_LEN:
        soft.append("요약 길이 미달")
    if len(actions) < C.MIN_ACTIONS:
        soft.append(f"실행 제안 개수 부족({len(actions)}/{C.MIN_ACTIONS})")
    if len(grounds) < C.MIN_REASONS:
        soft.append("근거 개수 부족")
    if grounds and not sources:
        soft.append("출처 미표기")

    if soft:
        return _result("warn", soft, _msg(soft))
    return _result("pass")


def _action_text(a) -> str:
    if isinstance(a, dict):
        return (a.get("content") or a.get("text") or "").strip()
    return str(a or "").strip()


# ═════════════════════════════════════════════════════════════════════════════
# 공개 API
# ═════════════════════════════════════════════════════════════════════════════
def self_check(result: dict, context: dict) -> dict:
    """LLM 답변의 근거 유무·완결성을 판정한다."""
    result = result or {}
    context = context or {}

    if not isinstance(result, dict) or not result:
        return _result(
            "reject",
            ["빈 결과"],
            "생성 결과가 비어 있습니다. 다시 시도해 주세요.",
        )

    # 기본 챗봇 — proposals / ranked_copies 어느 이름으로 와도 받는다
    for key in ("proposals", "ranked_copies"):
        if key in result:
            return _check_proposals(result.get(key) or [])

    # 컨설턴트
    if any(k in result for k in ("summary", "actions", "reasons")):
        return _check_strategy(result, context)

    # 알 수 없는 형태 — reject 하면 정상 응답을 되돌릴 위험이 있으므로 warn 이다
    return _result("warn", ["결과 형식 미상"], "생성 결과 형식을 확인하지 못했습니다.")
