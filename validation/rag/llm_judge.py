"""
validation/rag/llm_judge.py
2단 RAG 판정 — 검색된 조문을 근거로 "맥락상 위반인가"를 판단하고 대안 문구를 만든다.

★ 실패하면 예외를 던지지 않고 None 을 돌려준다.
  호출부(regulation.py)가 1단 결과로 degrade 할 수 있게 하기 위해서다 (D-271).
  여기서 raise 하면 파이프라인 전체가 error 로 끝난다.
"""

from __future__ import annotations

import json
import logging
import re
from functools import lru_cache

import openai

from .. import config as C

logger = logging.getLogger(__name__)

_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)

SYSTEM_PROMPT = """너는 한국 광고 규제 검토 담당자다. 소상공인이 쓴 광고 문구가
표시·광고의 공정화에 관한 법률, 식품 등의 표시·광고에 관한 법률에 위반되는지
'참고 조문'만을 근거로 판단한다.

판정 기준:
- pass  : 참고 조문 어디에도 해당하지 않는다. 일상적 품질 묘사·인사말·메뉴 이름은 pass다.
- warn  : 과장·효능·기만·부당비교 등 표현을 고치면 해결되는 경우.
- block : 마약류·무허가 의약품·도박·음란·위조품 등 판매 자체가 불법인 품목의 광고.

반드시 지킬 것:
1. 과장·효능·비교 표현은 아무리 심해도 block 이 아니라 warn 이다.
   block 은 '불법 품목' 카테고리 조문이 근거일 때만 쓴다.
2. 애매하면 pass 다. 정상 문구를 막는 것이 놓치는 것보다 나쁘다.
   ('최고급 원두', '최고의 하루 되세요', '마약김밥' 같은 관용 표현은 맥락을 본다)
3. warn 이면 alternative 에 '바로 쓸 수 있는 대체 광고 문구'를 쓴다.
   조언이 아니라 문구 그 자체여야 한다.
   ❌ "근거를 함께 밝히세요"   ✅ "3년 연속 재방문율 1위 (2023~2025 자체 집계)"
4. alternative 는 원문의 길이·말투를 유지한다. 원문이 짧으면 짧게 쓴다.
5. law 에는 참고 조문에 적힌 법령명과 조문 번호를 그대로 옮긴다. 지어내지 않는다.
6. 참고 조문에 근거가 없으면 pass 다.

JSON 만 출력한다. 설명·마크다운·코드펜스 금지.
{"verdict":"pass|warn|block","law":"","reason":"","alternative":"","trigger":""}
- reason 은 20자 이내 한국어 명사구 (예: "객관적 근거 없는 최상급 표현")
- trigger 는 문제가 된 원문 속 표현 그대로 (pass 면 "")"""



class JudgeConfigError(RuntimeError):
    """모델·파라미터 설정이 잘못됐다 — 재시도해도 안 되는 영구 실패다."""


def _call_judge(user_prompt: str) -> str:
    """팀 공용 call_llm() 으로 2단 판정을 호출한다.

    ★ 자체 OpenAI 클라이언트를 쓰지 않는 이유 (두 문제가 한 번에 풀린다)
      ① 토큰 집계 — call_llm 은 _total_tokens 에 모델별로 누적한다.
         직접 호출하면 $30 예산 추적에서 2단 사용량이 통째로 빠진다.
         실제로 judge 토큰이 계속 0 으로 찍혀 "2단이 안 돌았다" 로 오독됐다.
      ② 파라미터 세대 차이 — call_llm 은 max_tokens 를 아예 보내지 않는다.
         gpt-4o 계열이든 gpt-5 계열이든 400 이 나지 않는다.
         llm_judge 가 max_tokens=... 를 직접 넣은 것이 400 의 원인이었다.

    ★ 덤으로 얻는 것
      429 백오프·재시도 상한·deadline 처리가 call_llm 에 이미 있다(D-052).
      여기서 다시 구현할 이유가 없다.
    """
    from models.shared.llm import call_llm

    try:
        text, _tokens = call_llm(
            SYSTEM_PROMPT,
            user_prompt,
            json_mode=True,
            model=C.JUDGE_MODEL,
            temperature=C.JUDGE_TEMPERATURE,
        )
        return text
    except openai.BadRequestError as e:
        message = str(e)
        if "temperature" in message:
            # ⚠️ 이 모델은 temperature 고정을 지원하지 않는다 — 재현성이 깨진다(D-275)
            logger.error(
                "%s 는 temperature 고정을 지원하지 않는다. 기본값으로 재호출한다 — "
                "판정이 매번 달라질 수 있으므로 D-298 안정성 기준으로 확인하라.",
                C.JUDGE_MODEL,
            )
            # ⚠️ call_llm 은 temperature 를 생략할 수 없다(None 이면 기본값 0.3).
            #    이 모델은 1 만 허용하므로 명시적으로 1 을 넘긴다.
            text, _tokens = call_llm(
                SYSTEM_PROMPT, user_prompt, json_mode=True,
                model=C.JUDGE_MODEL, temperature=1.0,
            )
            return text
        raise JudgeConfigError(
            f"2단 판정 호출이 400 으로 거부됐다 — 설정을 고쳐야 한다.\n"
            f"  모델   : {C.JUDGE_MODEL}\n"
            f"  응답   : {message[:300]}\n"
            f"  → .env 의 VALIDATION_JUDGE_MODEL 을 확인한다"
            f"(OPENAI_JUDGE_MODEL 과 다른 값이다)."
        ) from e


def _build_user_prompt(copy: str, docs: list[dict], hints: list[str]) -> str:
    blocks = []
    for d in docs:
        blocks.append(
            f"[{d['id']}] {d['law']} / 카테고리: {d['category']} / 심각도: {d['severity']}\n"
            f"금지 내용: {d['text']}\n"
            f"위반 예시: {' / '.join(d.get('bad_examples', []))}\n"
            f"허용 예시: {' / '.join(d.get('good_examples', []))}\n"
            f"대안 가이드: {d.get('action_guide', '')}"
        )
    hint_line = f"\n1단 키워드 스크리닝에서 걸린 표현: {', '.join(hints)}" if hints else ""
    return (
        "## 참고 조문\n" + "\n\n".join(blocks)
        + f"\n\n## 검토할 광고 문구\n{copy}{hint_line}\n\n## 출력\nJSON 만."
    )


def _parse(raw: str) -> dict | None:
    txt = _FENCE.sub("", (raw or "").strip())
    start, end = txt.find("{"), txt.rfind("}")
    if start == -1 or end == -1:
        return None
    try:
        data = json.loads(txt[start:end + 1])
    except json.JSONDecodeError:
        return None
    if data.get("verdict") not in ("pass", "warn", "block"):
        return None
    return {
        "verdict": data["verdict"],
        "law": str(data.get("law") or ""),
        "reason": str(data.get("reason") or ""),
        "alternative": str(data.get("alternative") or ""),
        "trigger": str(data.get("trigger") or ""),
    }


@lru_cache(maxsize=C.JUDGE_CACHE_SIZE)
def _cached_call(copy: str, doc_key: str, hint_key: str) -> str | None:
    """LLM 호출 결과 원문을 캐시한다.

    ★ 캐시가 없으면 카피 재생성 루프(최대 2회)와 골든 평가 반복 실행에서
      같은 문구에 대해 OpenAI 를 계속 호출하게 된다. $30 한도에서 치명적이다.
    """
    from .legal_retriever import by_id

    idx = by_id()
    docs = [idx[i] for i in doc_key.split(",") if i in idx]
    hints = [h for h in hint_key.split("|") if h]

    try:
        raw = _call_judge(_build_user_prompt(copy, docs, hints))
        return raw
    except JudgeConfigError:
        # ★ 설정 오류는 degrade 하지 않고 그대로 올린다.
        #   재시도해도 영원히 안 되는 실패를 "일시 장애" 로 감추면
        #   2단이 안 도는 상태로 평가가 끝나고 아무도 모른다.
        raise
    except Exception as e:  # noqa: BLE001
        logger.warning("LLM 판정 실패 → 1단 결과로 degrade: %s", type(e).__name__)
        return None


def judge(copy: str, docs: list[dict], hints: list[str]) -> dict | None:
    """맥락 판정. 실패하면 None (호출부가 degrade)."""
    if not C.RAG_ENABLED or not C.has_openai_key() or not docs:
        return None
    raw = _cached_call(copy, ",".join(d["id"] for d in docs), "|".join(hints))
    if raw is None:
        return None
    parsed = _parse(raw)
    if parsed is None:
        logger.warning("LLM 판정 JSON 파싱 실패 → degrade")
    return parsed
