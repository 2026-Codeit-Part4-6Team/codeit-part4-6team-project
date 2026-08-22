"""
models/basic/main.py
— 서비스 계약 진입점 (D-206: 모델은 동기 run() 을 제공하고 서비스가 asyncio.to_thread 로 감싼다)

★ run() 의 유일한 계약: **절대 예외를 던지지 않고, 항상 세 형태 중 하나를 반환한다.**
    {"status":"ok",      ...}
    {"status":"error",   "reason": <ErrorResult enum 4종>, "message": str}
    {"status":"blocked", "action": <block|reask|warn>, "reason": str, "message": str}
  예외가 새어 나가면 서비스가 ModelResult 가 아닌 것을 받아 ErrorResult(v0.3 §6.6)
  계약을 만족할 수 없다.
"""

from __future__ import annotations

import logging
import time
from typing import Any

from models.basic.graph.build_basic import build_basic_graph
from models.shared.config import LLM_DEADLINE_SECONDS
from models.shared.llm_errors import classify_llm_error

logger = logging.getLogger(__name__)

# ── 계약 enum (v0.3 §6.5·§6.6) ───────────────────────────────────────────────
_ERROR_REASONS = ("timeout", "rate_limit", "provider_error", "unknown")
_BLOCKED_ACTIONS = ("block", "reask", "warn")

# 내부 reason → 계약 reason. D-073 확정 매핑, 목록 밖은 unknown(D-214).
# ⚠️ copy_generation_failed 는 D-073 에서 provider_error 로 확정됐다.
#    unknown 으로 바꾸려면 코드가 아니라 decisions.md 에서 먼저 뒤집는다(D-046).
_ERROR_REASON_MAP = {
    "copy_generation_failed": "provider_error",
    "timeout": "timeout",
    "rate_limit": "rate_limit",
    "provider_error": "provider_error",
    "unknown": "unknown",
}

# 서비스가 Pydantic 으로 검증하지만(state_common.py 주석), 여기서 먼저 막으면
# LLM 호출 0회·비용 0원으로 끝난다. platform 은 Basic 필수다(D-083).
_REQUIRED_KEYS = ("chatbot_type", "user_id", "question", "platform", "store")

# ── 그래프 싱글턴 ────────────────────────────────────────────────────────────
# ★ 매 요청마다 build_basic_graph() 를 부르면 요청 수만큼 StateGraph 를 다시
#   컴파일한다. llm.py 의 _get_client() 가 클라이언트를 1회만 만드는 것과 같은 이유다.
#   D-206 으로 서비스가 asyncio.to_thread 를 쓰므로 동시 요청이 여러 스레드에서
#   들어온다 — 요청마다 컴파일하면 p50 응답시간(§6 지표)이 그대로 늘어난다.
_graph: Any = None


def _get_graph() -> Any:
    global _graph
    if _graph is None:
        _graph = build_basic_graph()
    return _graph


def reset_graph() -> None:
    """테스트에서 캐시된 그래프를 비운다(llm.py::reset_client 와 같은 역할)."""
    global _graph
    _graph = None


# ── 진입점 ───────────────────────────────────────────────────────────────────
def run(request: dict) -> dict:
    """ModelRequest dict 를 받아 ModelResult dict 를 반환한다."""
    # [1단] 요청 구성 — 그래프 실행 실패와 원인을 분리한다.
    #       하나의 try 로 묶으면 로그만 보고 "요청이 잘못된 건지 모델이 죽은 건지"
    #       판단할 수 없다.
    try:
        initial_state = _build_initial_state(request)
    except Exception:
        logger.exception("기본 챗봇 요청 구성 실패 — request 키 확인 필요!")
        return _error("unknown", "요청 형식이 올바르지 않습니다.")

    # [2단] 그래프 실행 + 응답 조립
    try:
        final_state = _get_graph().invoke(initial_state)
        return assemble_response(final_state)
    except Exception as exc:
        # warning() 은 exc 의 문자열만 남겨 실제 버그의 호출 경로(traceback)가 사라진다 —
        # exception() 으로 전체 traceback 을 남겨야 나중에 원인을 추적할 수 있다.
        logger.exception("기본 챗봇 파이프라인 실행 실패")
        return _error(classify_llm_error(exc), "카피/이미지 생성 중 오류가 발생했습니다.")


def _build_initial_state(request: dict) -> dict:
    missing = [k for k in _REQUIRED_KEYS if request.get(k) in (None, "")]
    if missing:
        raise KeyError(f"필수 키 누락: {missing}")
    return {
        "chatbot_type": request["chatbot_type"],
        "user_id": request["user_id"],
        "question": request["question"],
        "platform": request["platform"],
        "store": request["store"],
        "extra": request.get("extra") or {},
        # 컨설팅→광고 파생 추적(v10). 넘기지 않으면 연계 경로가 끊긴다.
        "source_gen_id": request.get("source_gen_id"),
        # D-144 — 그래프 전체 시간 예산. 이게 없으면 재생성 2회 + self_check 1회 +
        # 429 백오프(2→4→8초)가 서비스 타임아웃 60초를 잠식해 504 가 난다.
        "deadline": time.monotonic() + LLM_DEADLINE_SECONDS,
        "tokens_used": 0,
    }


# ── 응답 조립 ────────────────────────────────────────────────────────────────
def assemble_response(state: dict) -> dict:
    """파이프라인 최종 상태를 API 응답 형식(ok/error/blocked)으로 변환한다."""
    # ★ state["status"] 로 읽으면 안 된다.
    #   validation_contract.md 검증 함수 계약서 §8 의 노드는 pass 일 때 status 를 세팅하지 않는다(부분 업데이트만 반환).
    #   즉 **정상 통과한 요청에는 status 키가 아예 없어** KeyError → 전 요청이 error 로 나간다.
    #   컨설턴트 assemble_response 가 .get("status","ok") 를 쓰는 이유다(P-036).
    status = state.get("status", "ok")

    if status == "ok" and not state.get("result"):
        status = "error"

    if status == "ok":
        result = dict(state["result"])
        # result 안에 status 가 섞여 들어오면 "ok" 를 덮어쓴다 — 먼저 제거한다.
        result.pop("status", None)
        return {
            "status": "ok",
            **result,
            # ★ sources 는 NotRequired 라 조회 노드가 하나도 안 돌면 키가 없다.
            #   .get() 만 쓰면 None 이 나가고 서비스 Pydantic(list[str])에서 502 다.
            "sources": state.get("sources") or [],
            "tokens_used": state.get("tokens_used", 0),
        }

    last_issue = (state.get("issues") or [{}])[-1]

    if status == "error":
        reason = _ERROR_REASON_MAP.get(last_issue.get("reason"), "unknown")
        return _error(reason, last_issue.get("message") or "모델 처리 중 오류가 발생했습니다.")

    if status != "blocked":
        # Model status 는 ok·blocked·error 세 가지뿐이다(§12.1).
        # 오타나 Generation status 가 섞여 들어오면 조용히 blocked 로 떨어뜨리지 않는다.
        logger.error("알 수 없는 status=%r — error 로 처리한다", status)
        return _error("unknown", "모델 처리 중 오류가 발생했습니다.")

    # blocked — ★ D-215 는 message 만 막았다. action·reason 도 같은 이유로 막는다.
    #   BlockedResult.action 은 enum(block·reask·warn)이고 reason 은 필수라
    #   None 이 나가면 D-073 과 같은 유형의 502 가 된다.
    action = last_issue.get("action")
    if action not in _BLOCKED_ACTIONS:
        logger.error("blocked 인데 action=%r — block 으로 폴백한다", action)
        action = "block"
    reason = last_issue.get("reason")
    if not reason:
        logger.error("blocked 인데 reason 이 비었다 — issues 를 채우지 않은 노드가 있다")
        reason = "unknown"
    return {
        "status": "blocked",
        "action": action,
        "reason": reason,
        "message": last_issue.get("message") or "요청을 처리할 수 없습니다.",
    }


def _error(reason: str, message: str) -> dict:
    return {
        "status": "error",
        "reason": reason if reason in _ERROR_REASONS else "unknown",
        "message": message,
    }
