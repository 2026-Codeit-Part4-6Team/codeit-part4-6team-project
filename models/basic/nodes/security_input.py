from validation.security import check_input

from ..graph.state import BasicState


def security_input_node(state: BasicState) -> dict:
    checked = check_input(state["question"])
    validation = {**state.get("validation", {}), "input": checked}

    updates = {"validation": validation}
    if checked.get("action") == "block":
        updates["status"] = "blocked"
        updates["issues"] = state.get("issues", []) + [
            {
                "source": "input",
                "action": checked.get("action"),
                "reason": "input_blocked",
                "message": checked.get("message", ""),
            }
        ]
    return updates
