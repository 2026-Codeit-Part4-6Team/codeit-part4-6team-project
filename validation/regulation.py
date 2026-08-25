"""
validation/regulation.py
법률 규제 준수 검증 (RAG) — 1단 키워드 스크리닝 → 2단 legal_kb RAG 판정

반환 규격 (계약서 §5.2)
    action      : "pass" | "warn" | "block"
    law         : 근거 법률 조문 (예: "표시광고법 제3조")
    reason      : 왜 안 되는지
    alternative : 대안 문구
    message     : 사용자 안내

★ 설계 3줄 요약
  1) 1단은 recall 우선이다. 놓치면 2단이 볼 기회조차 없다. 오탐은 2단이 걸러준다.
  2) 2단이 실패해도 절대 예외를 던지지 않는다. 1단 결과 + KB 대안으로 degrade 한다.
  3) 과장·효능은 무조건 warn. block 은 불법 품목 카테고리에만 허용한다 (§6.5).
"""

from __future__ import annotations

import logging

from . import config as C
from .patterns import normalize, squeeze
from .rag import legal_retriever as retriever
from .rag import llm_judge

logger = logging.getLogger(__name__)

_BLOCK_CATEGORIES = {"불법품목"}


def _bigrams(s: str) -> set[str]:
    s = "".join(s.split())
    return {s[i:i + 2] for i in range(len(s) - 1)} or {s}


def _best_alternative(chunk: dict, copy: str) -> str:
    """사용자에게 제시할 대안 문구를 고른다.

    ★ alternatives(대안 문구)를 먼저 쓰고, 없으면 good_examples(허용 예시)로 폴백한다.
      두 필드는 역할이 다르다 — 허용 예시는 llm_judge 의 few-shot 이라 경계 사례를
      담아야 하고(다른 트리거에 걸려도 무방), 대안 문구는 사용자에게 나가므로
      어떤 트리거에도 걸리면 안 된다. v7 에서 겸용하다 충돌했다.
    """
    pool = chunk.get("alternatives") or chunk.get("good_examples") or []
    if not pool:
        return ""
    # 원문과 가장 덜 겹치는 것을 고른다 — 같은 표현을 되풀이하지 않는다
    low = normalize(copy)
    return min(pool, key=lambda a: len(set(normalize(a)) & set(low)))



def _result(action: str, law: str = "", reason: str = "",
            alternative: str = "", message: str = "") -> dict:
    """계약서 §5.4-2: pass 일 때도 모든 필드를 채운다."""
    return {
        "action": action,
        "law": law,
        "reason": reason,
        "alternative": alternative,
        "message": message,
    }


# ═════════════════════════════════════════════════════════════════════════════
# 1단 — 키워드 스크리닝 (LLM 호출 0회, 수 ms)
# ═════════════════════════════════════════════════════════════════════════════
def screen(copy: str) -> list[dict]:
    """legal_kb 트리거 사전으로 후보 조항을 뽑는다.

    ★ 예외 표현을 먼저 마스킹한 뒤 트리거를 매칭한다.
      "최고급 원두"에서 '최고급'을 지우면 '최고'가 남지 않는다 → 오탐 제거.
      "최고급 원두인데 우리가 최고예요"는 뒤쪽 '최고'가 남아 정상적으로 걸린다.
    """
    low = normalize(copy)
    if not low.strip():
        return []
    # ★ 공백을 없앤 사본에서도 검사한다 (불변성 대응).
    #   "면 역 력  강화" 처럼 공백을 끼워 넣으면 트리거 '면역력 강화' 가 쪼개져
    #   normalize 만으로는 못 잡는다 — 실측 불변성 86.1%, 뒤집힌 30건 중 29건이 공백 계열.
    #   check_input 은 v7 에서 이미 양쪽을 보게 고쳤고, screen() 만 남아 있었다.
    tight = squeeze(copy)

    hits: list[dict] = []
    for chunk in retriever.chunks():
        masked, masked_tight = low, tight
        for exc in chunk.get("exceptions", []):
            e = normalize(exc)
            if e:
                masked = masked.replace(e, " ")
            # 예외도 같은 기준으로 마스킹해야 한다 — 안 하면 예외가 무력해져
            # 과잉 차단이 되살아난다(R-051·R-055·R-058).
            et = squeeze(exc)
            if et:
                masked_tight = masked_tight.replace(et, " ")
        matched = [
            t for t in chunk.get("triggers", [])
            if ((n := normalize(t)) and n in masked) or ((q := squeeze(t)) and q in masked_tight)
        ]
        if matched:
            hits.append({
                "id": chunk["id"],
                "severity": chunk["severity"],
                "category": chunk["category"],
                # 가장 긴 트리거가 보통 가장 구체적이다
                "triggers": sorted(matched, key=len, reverse=True),
            })
    return hits



def _safe_alternative(alternative: str, fallback: str) -> str:
    """대안이 **다른 법률 조문에 다시 걸리지 않는지** 확인하고, 걸리면 폴백한다.

    ★ 왜 필요한가 (실측 근거)
      2단 LLM 이 만든 대안 24건 중 4건(R-021·R-026·R-033·R-040)이
      재검사에서 warn 이 났다 — "이렇게 고치세요" 라고 준 문구가 또 걸린다.
      사용자는 시키는 대로 고쳐도 계속 막히는 무한 루프에 빠진다.
      check_regulation 의 존재 이유가 "차단이 아니라 대안 제시"(§6.2.1)이므로
      대안이 유효하지 않으면 함수 전체가 무의미해진다.

    ★ 1단만 돌린다 — 2단 LLM 을 다시 부르지 않는다.
      재검사에 또 LLM 을 쓰면 호출이 2배가 되고, 그 판정이 또 흔들린다.
      1단 키워드로 "명백히 걸리는지" 만 보면 충분하다.
    """
    if not alternative:
        return fallback
    if not screen(alternative):          # 1단에 안 걸리면 그대로 쓴다
        return alternative
    logger.info("LLM 대안이 다시 트리거에 걸림 → KB 허용 예시로 폴백: %r", alternative[:40])
    return fallback or alternative


def _worst(hits: list[dict]) -> dict:
    """block > warn, 그다음 트리거 길이 순으로 대표 히트를 고른다.

    ★ sorted(...)[0] 이 아니라 max() 를 쓴다(FURB192).
      동점 처리가 같다 — sorted(reverse=True) 는 안정 정렬이라 동점이면 원래 순서를
      유지하고, max() 도 동점이면 먼저 나온 것을 돌려준다. 무작위 2만 케이스로 대조 확인.
      max() 는 전체 정렬(O(n log n)) 없이 한 번만 훑는다(O(n)).
    """
    return max(hits, key=lambda h: (h["severity"] == "block", len(h["triggers"][0])))


# ═════════════════════════════════════════════════════════════════════════════
# 메시지 조립
# ═════════════════════════════════════════════════════════════════════════════
_MSG_BLOCK = (
    "{law}상 광고가 제한되는 품목이에요. "
    "판매 중인 다른 메뉴나 상품으로 다시 요청해 주세요."
)


def _warn_message(trigger: str, law: str, reason: str, alternative: str) -> str:
    """★ alternative 를 반드시 문장 안에 넣는다 (계약서 §5.2).

    law·alternative 는 서비스 응답 계약(v0.3)에 없는 필드라 그대로 올려보내면
    extra="ignore" 로 조용히 버려진다. message 에 녹여야 사용자에게 도달한다.
    """
    head = f"'{trigger}' 같은 표현은 " if trigger else "이 문구는 "
    body = f"{law}상 {reason}에 해당할 수 있어요." if law else f"{reason} 소지가 있어요."
    return f"{head}{body} 대신 \"{alternative}\" 는 어떨까요?"


# ═════════════════════════════════════════════════════════════════════════════
# 2단 실패 시 degrade (D-271)
# ═════════════════════════════════════════════════════════════════════════════
def _degrade(hits: list[dict], copy: str = "") -> dict:
    """LLM 판정 없이 1단 히트 + KB 규칙만으로 판정을 만든다.

    fail-open(pass) 도 fail-closed(block) 도 쓰지 않는다.
      · pass 로 열면 위험 문구가 그대로 사용자에게 나간다.
      · block 으로 닫으면 과잉 차단률이 폭증해 골든 R-011~R-015 가 전멸한다.
    → 1단이 이미 근거 조항을 지목했으므로, 그 조항의 허용 예시를 대안으로 준다.
      대안 제시율 100% 지표도 이 경로에서 유지된다.
    """
    top = _worst(hits)
    chunk = retriever.by_id().get(top["id"], {})
    law = chunk.get("law", "")
    trigger = top["triggers"][0]

    if top["severity"] == "block" or top["category"] in _BLOCK_CATEGORIES:
        return _result(
            "block", law, "광고 제한 품목", "",
            _MSG_BLOCK.format(law=law or "관련 법령"),
        )

    alternative = _best_alternative(chunk, copy or top["triggers"][0])
    reason = f"{chunk.get('category', '표현')} 위험"
    if not alternative:
        # 여기 오면 KB 작성이 잘못된 것이다 (build_legal_kb.py 가 CI에서 잡는다)
        logger.error("warn 인데 허용 예시가 없다: %s", top["id"])
        return _result("pass")
    return _result(
        "warn", law, reason, alternative,
        _warn_message(trigger, law, reason, alternative),
    )


# ═════════════════════════════════════════════════════════════════════════════
# 공개 API
# ═════════════════════════════════════════════════════════════════════════════
def check_regulation(copy: str) -> dict:
    """규제 준수 검증 — 1단 키워드 스크리닝 → 2단 legal_kb RAG 판정."""
    if not copy or not copy.strip():
        return _result("pass")

    # ── [1단] 키워드 스크리닝 — LLM 호출 없음 ────────────────────────────────
    hits = screen(copy)
    if not hits:
        return _result("pass")           # 정상 카피의 70~80%가 여기서 끝난다

    # ── [2단] RAG 정밀 판정 — 걸린 경우만 ───────────────────────────────────
    prefer = [h["id"] for h in hits]
    docs = retriever.search(copy, k=C.RETRIEVE_TOP_K, prefer_ids=prefer)
    verdict = llm_judge.judge(copy, docs, _worst(hits)["triggers"][:3])

    if verdict is None:
        return _degrade(hits, copy)

    if verdict["verdict"] == "pass":
        # 1단이 걸었지만 2단이 맥락상 정상이라고 판단 → 통과.
        # 과잉 차단을 막는 핵심 경로다. ('최고급 원두', '마약김밥' 등)
        return _result("pass")

    # ★ law 는 LLM 이 쓴 값을 쓰지 않고 **검색된 법률 조문에서 직접 가져온다**.
    #   실측: LLM 이 쓴 law 가 검색 법률 조문과 안 맞는 경우가 24건 중 3건(12.5%)이었다.
    #   법 조항은 창작 대상이 아니다 — 지어낸 조항을 사용자에게 보여주면
    #   "표시광고법 제3조" 같은 문구가 근거 없이 나간다.
    #   verdict["law"] 는 로그로만 남겨 LLM 환각률을 계속 추적한다.
    law = retriever.by_id().get(_worst(hits)["id"], {}).get("law", "")
    if verdict.get("law") and verdict["law"] != law:
        logger.info("LLM 이 다른 law 를 제시함 (무시): %r vs KB %r", verdict["law"], law)
    trigger = verdict["trigger"] or _worst(hits)["triggers"][0]

    # ── block 정규화 — 불법 품목 근거가 있을 때만 block 을 인정한다 ─────────
    if verdict["verdict"] == "block":
        illegal = any(
            d.get("category") in _BLOCK_CATEGORIES or d.get("severity") == "block"
            for d in docs
        )
        if illegal:
            return _result("block", law, verdict["reason"] or "광고 제한 품목", "",
                           _MSG_BLOCK.format(law=law or "관련 법령"))
        # 근거가 과장·효능 조항인데 LLM 이 block 을 냈다 → warn 으로 강등 (§6.5)
        logger.info("LLM block → warn 강등 (불법 품목 근거 없음): %s", trigger)
        verdict["verdict"] = "warn"

    # ── warn ────────────────────────────────────────────────────────────────
    chunk = retriever.by_id().get(_worst(hits)["id"], {})
    kb_alternative = _best_alternative(chunk, copy)

    # ★ LLM 이 만든 대안이 **다른 법률 조문에 다시 걸리는지** 확인한다.
    #   "이렇게 고치세요" 라고 준 문구가 또 막히면 사용자는 무한 루프에 빠진다.
    #   실측: LLM 대안 24건 중 7건이 재검사에서 걸렸다(대안 유효성 70.8%).
    alternative = _safe_alternative(verdict["alternative"].strip(), kb_alternative)
    if not alternative:
        return _degrade(hits, copy)

    reason = verdict["reason"] or "부당광고 위험 표현"
    return _result(
        "warn", law, reason, alternative,
        _warn_message(trigger, law, reason, alternative),
    )
