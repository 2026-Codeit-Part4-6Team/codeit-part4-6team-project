from validation.self_check import self_check

from ..graph.state import BasicState


def self_check_node(state: BasicState) -> dict:
    """최종 응답 결과가 요청 맥락에 부합하는지 자가 점검하고,
    반려 판정이면 상태를 blocked로 전환한다."""
    result_payload = state.get("result") or {}
    context = state.get("context") or {}

    outcome = self_check(result_payload, context)
    validation = {**state.get("validation", {}), "self_check": outcome}

    updates = {"validation": validation}
    if outcome.get("action") == "reject":
        updates["status"] = "blocked"
        updates["issues"] = state.get("issues", []) + [
            {
                "source": "self_check",
                "action": "block",
                "reason": "self_check_failed",
                "message": outcome.get("message", ""),
            }
        ]
    return updates
