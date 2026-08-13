from validation.self_check import self_check

from ..graph.state import BasicState


def self_check_node(state: BasicState) -> dict:
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
