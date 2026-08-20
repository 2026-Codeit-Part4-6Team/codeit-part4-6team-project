import logging

from models.basic.graph.build_basic import build_basic_graph
from models.shared.llm_errors import classify_llm_error

logger = logging.getLogger(__name__)

_ERROR_REASON_MAP = {
    "copy_generation_failed": "unknown",
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
        initial_state = {
            "chatbot_type": request["chatbot_type"],
            "user_id": request["user_id"],
            "question": request["question"],
            "platform": request["platform"],
            "store": request["store"],
            "extra": request.get("extra") or {},
            "tokens_used": 0,
        }
        final_state = build_basic_graph().invoke(initial_state)
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


def assemble_response(state):
    """파이프라인 최종 상태를 API 응답 형식(ok/error/blocked)으로 변환한다."""
    status = state["status"]
    if status == "ok" and not state.get("result"):
        status = "error"

    if status == "ok":
        return {
            "status": "ok",
            **state["result"],
            "sources": state.get("sources"),
            "tokens_used": state.get("tokens_used", 0),
        }

    if status == "error":
        last_issue = (state.get("issues") or [{}])[-1]
        reason = _ERROR_REASON_MAP.get(last_issue.get("reason"), "unknown")
        return {
            "status": "error",
            "reason": reason,
            "message": last_issue.get("message") or "모델 처리 중 오류가 발생했습니다.",
        }

    # blocked
    last_issue = (state.get("issues") or [{}])[-1]
    return {
        "status": "blocked",
        "action": last_issue.get("action"),
        "reason": last_issue.get("reason"),
        "message": last_issue.get("message") or "요청을 처리할 수 없습니다.",
    }
