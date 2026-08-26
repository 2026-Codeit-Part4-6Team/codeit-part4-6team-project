import logging
import time
from typing import Any

from models.basic.graph.build_basic import build_basic_graph
from models.shared.config import LLM_DEADLINE_SECONDS
from models.shared.llm_errors import classify_llm_error

logger = logging.getLogger(__name__)

_graph: Any = None


def _get_graph() -> Any:
    global _graph
    if _graph is None:
        _graph = build_basic_graph()
    return _graph


def reset_graph() -> None:
    """테스트에서 캐시된 그래프를 비운다(llm.py::reset_client와 같은 역할)."""
    global _graph
    _graph = None


_ERROR_REASON_MAP = {
    "copy_generation_failed": "provider_error",
    "timeout": "timeout",
    "rate_limit": "rate_limit",
    "provider_error": "provider_error",
}


def run(request: dict) -> dict:
    """ModelRequest dict를 받아 ModelResult dict를 반환한다.

    request 구성이나 그래프 실행, 응답 조립(assemble_response) 중 어디서
    실패하든 서비스에는 항상 계약을 지키는 dict를 돌려준다 — 예외를 그대로
    올리면 서비스가 ModelResult가 아닌 것을 받게 되어 ErrorResult(§6.6)
    계약을 만족할 수 없다.
    """
    try:
        initial_state = _build_initial_state(request)
        final_state = _get_graph().invoke(initial_state)
        return assemble_response(final_state)
    except Exception as exc:
        # warning()은 exc의 문자열만 남겨 실제 버그의 호출 경로(traceback)가 사라진다 —
        # exception()으로 전체 traceback을 남겨야 나중에 원인을 추적할 수 있다.
        logger.exception("기본 챗봇 파이프라인 실행 실패")
        return {
            "status": "error",
            "reason": classify_llm_error(exc),
            "message": "카피/이미지 생성 중 오류가 발생했습니다.",
        }


def _build_initial_state(request: dict) -> dict:
    return {
        "chatbot_type": request["chatbot_type"],
        "user_id": request["user_id"],
        "question": request["question"],
        "platform": request["platform"],
        "store": request["store"],
        "extra": request.get("extra") or {},
        # 컨설팅→광고 파생 추적(v10). 넘기지 않으면 연계 경로가 끊긴다.
        "source_context": request.get("source_context"),
        "deadline": time.monotonic() + LLM_DEADLINE_SECONDS,
        "tokens_used": 0,
    }


def assemble_response(state):
    """파이프라인 최종 상태를 API 응답 형식(ok/error/blocked)으로 변환한다."""
    status = state.get("status", "ok")
    if status == "ok" and not state.get("result"):
        status = "error"

    if status == "ok":
        return {
            **state["result"],
            "sources": state.get("sources") or [],
            "tokens_used": state.get("tokens_used", 0),
            "status": "ok",
        }

    if status == "error":
        last_issue = (state.get("issues") or [{}])[-1]
        reason = _ERROR_REASON_MAP.get(last_issue.get("reason"), "unknown")
        return {
            "status": "error",
            "reason": reason,
            "message": last_issue.get("message") or "모델 처리 중 오류가 발생했습니다.",
        }

    if status != "blocked":
        logger.error("알 수 없는 status=%r — error로 처리한다", status)
        return {
            "status": "error",
            "reason": "unknown",
            "message": "모델 처리 중 오류가 발생했습니다.",
        }

    # blocked
    last_issue = (state.get("issues") or [{}])[-1]
    action = last_issue.get("action")
    if action not in ("block", "reask", "warn"):
        action = "block"
    reason = last_issue.get("reason") or "unknown"
    return {
        "status": "blocked",
        "action": action,
        "reason": reason,
        "message": last_issue.get("message") or "요청을 처리할 수 없습니다.",
    }
