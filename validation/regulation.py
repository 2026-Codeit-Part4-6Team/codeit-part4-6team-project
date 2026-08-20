"""
validation/regulation.py
규제 준수 검증 (RAG) — 1단 키워드 스크리닝 → 2단 legal_kb RAG 판정

반환 규격 (계약서 §5.2)
    action      : "pass" | "warn" | "block"
    law         : 근거 조문 (예: "표시광고법 제3조")
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
from .patterns import normalize
from .rag import legal_retriever as retriever
from .rag import llm_judge

logger = logging.getLogger(__name__)

_BLOCK_CATEGORIES = {"불법품목"}


def _bigrams(s: str) -> set[str]:
    s = "".join(s.split())
    return {s[i:i + 2] for i in range(len(s) - 1)} or {s}


def _best_alternative(chunk: dict, copy: str) -> str:
    """허용 예시 중 입력 카피와 가장 가까운 것을 고른다.

    ★ good_examples[0] 을 그냥 쓰면 엉뚱한 대안이 나간다.
      REG-027 은 허용 예시가 '점심 11~14시 전 메뉴 50% 할인' / '3만원 이상 주문 시
      배달비 무료' 두 개인데, 입력이 "무료 배달"인데 앞의 것을 주면 사용자는
      "이게 왜 대안이지?" 가 된다. 대안 제시율은 100%여도 쓸모가 0이 된다.
    """
    goods = [g for g in (chunk.get("good_examples") or []) if g.strip()]
    if len(goods) <= 1:
        return goods[0] if goods else ""
    cb = _bigrams(normalize(copy))
    best = max(goods, key=lambda g: len(cb & _bigrams(normalize(g))))
    # 겹침이 1개뿐이면 '~니다' 같은 어미가 우연히 맞은 것이다.
    # 이때는 KB 작성자가 첫 번째로 둔 대표 대안을 쓴다.
    return best if len(cb & _bigrams(normalize(best))) >= 2 else goods[0]


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

    hits: list[dict] = []
    for chunk in retriever.chunks():
        masked = low
        for exc in chunk.get("exceptions", []):
            e = normalize(exc)
            if e:
                masked = masked.replace(e, " ")
        matched = [t for t in chunk.get("triggers", []) if (n := normalize(t)) and n in masked]
        if matched:
            hits.append({
                "id": chunk["id"],
                "severity": chunk["severity"],
                "category": chunk["category"],
                # 가장 긴 트리거가 보통 가장 구체적이다
                "triggers": sorted(matched, key=len, reverse=True),
            })
    return hits


def _worst(hits: list[dict]) -> dict:
    """block > warn, 그다음 트리거 길이 순으로 대표 히트를 고른다."""
    return max(
        hits,
        key=lambda h: (h["severity"] == "block", len(h["triggers"][0])),
    )


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

    law = verdict["law"] or retriever.by_id().get(hits[0]["id"], {}).get("law", "")
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
    alternative = verdict["alternative"].strip()
    if not alternative:
        chunk = retriever.by_id().get(_worst(hits)["id"], {})
        alternative = _best_alternative(chunk, copy)
    if not alternative:
        return _degrade(hits, copy)

    reason = verdict["reason"] or "부당광고 위험 표현"
    return _result(
        "warn", law, reason, alternative,
        _warn_message(trigger, law, reason, alternative),
    )
