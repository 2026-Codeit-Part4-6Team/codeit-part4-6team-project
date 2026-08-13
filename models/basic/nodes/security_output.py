from validation.security import check_output

from ..graph.state import BasicState


def security_output_node(state: BasicState) -> dict:
    generated_text = "\n".join(
        c["copy"] for c in state["ranked_copies"] if c.get("copy")
    )
    checked = check_output(generated_text)
    validation = {**state.get("validation", {}), "output": checked}

    updates = {"validation": validation}
    if checked.get("action") == "block":
        updates["status"] = "blocked"
        updates["issues"] = state.get("issues", []) + [
            {
                "source": "output",
                "action": checked.get("action"),
                "reason": "output_blocked",
                "message": checked.get("message", ""),
            }
        ]
    return updates
