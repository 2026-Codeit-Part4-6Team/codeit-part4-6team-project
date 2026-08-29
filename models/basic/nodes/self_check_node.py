import logging

from validation.self_check import self_check

from ..graph.state import BasicState

logger = logging.getLogger(__name__)


def self_check_node(state: BasicState) -> dict:
    """최종 응답 결과가 요청 맥락에 부합하는지 자가 점검한다.

    reject는 재시도 없이 즉시 차단한다(D-413) — self_check_retry_count는
    관찰용으로만 남기고 재시도 여부 판단에는 쓰지 않는다. reason은 계약
    enum 밖이라 "unknown"으로 내보낸다(D-157).

    warn(카피 개수 부족·길이 미달·중복 등 품질 경고)은 차단하지 않고 로그만 남긴다.
    """
    result_payload = state.get("result") or {}
    context = state.get("context") or {}

    outcome = self_check(result_payload, context)
    validation = {**state.get("validation", {}), "self_check": outcome}

    updates = {"validation": validation}
    if outcome.get("action") == "warn":
        logger.warning(
            "self_check warn — reasons=%s message=%s",
            outcome.get("reasons"),
            outcome.get("message"),
        )

    if outcome.get("action") == "reject":
        updates["self_check_retry_count"] = state.get("self_check_retry_count", 0) + 1
        updates["status"] = "blocked"
        updates["issues"] = state.get("issues", []) + [
            {
                "source": "self_check",
                "action": "block",
                "reason": "unknown",
                "message": outcome.get("message") or "생성 결과 검증에 실패했습니다.",
            }
        ]

    return updates
