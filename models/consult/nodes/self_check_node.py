# self_check 노드 — 전민재 PM의 self_check() 판정을 컨설턴트 흐름에 반영
import logging

from models.consult.config import SELF_CHECK_MAX_RETRY
from models.consult.graph.state import ConsultState
from validation.self_check import self_check

logger = logging.getLogger(__name__)


def self_check_node(state: ConsultState) -> dict:
    """전략 결과의 근거·완결성을 검증하고 warn·reject 판정을 반영한다.

    result·context가 아직 채워지지 않은 상태에서도 죽지 않도록 빈 dict로
    안전하게 폴백한다. warn은 로그만 남기고 반환하며, reject는 전략을 최대
    1회 재생성한 뒤 다시 실패하면 계약상 ErrorResult로 종료한다.
    """
    result = state.get("result", {})
    context = dict(state.get("context", {}))
    if state.get("sources"):
        context["sources"] = state["sources"]
    verdict = self_check(result, context)
    updates = {
        "validation": {**state.get("validation", {}), "self_check": verdict}
    }

    action = verdict.get("action")
    if action == "warn":
        logger.warning(
            "self_check warn — reasons=%s message=%s",
            verdict.get("reasons"),
            verdict.get("message"),
        )
        return updates

    if action != "reject":
        return updates

    retry_count = state.get("self_check_retry_count", 0)
    if retry_count < SELF_CHECK_MAX_RETRY:
        updates["self_check_retry_count"] = retry_count + 1
        return updates

    updates["status"] = "error"
    updates["issues"] = state.get("issues", []) + [
        {
            "source": "self_check",
            "action": "block",
            "reason": "unknown",
            "message": verdict.get("message") or "생성 결과 검증에 실패했습니다.",
        }
    ]
    return updates
