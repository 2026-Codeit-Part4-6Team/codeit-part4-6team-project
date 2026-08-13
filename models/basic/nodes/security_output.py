from validation.security import check_output

from ..graph.state import BasicState


def security_output_node(state: BasicState) -> dict:
    """생성된 카피 전체 텍스트에 대해 출력 보안 검사를 수행하고,
    차단 판정이면 상태를 blocked로 전환한다."""
    generated_text = "\n".join(
        c["copy"] for c in state["ranked_copies"] if c.get("copy")
    )
    checked = check_output(generated_text)
    validation = {**state.get("validation", {}), "output": checked}

    updates = {"validation": validation}
    if checked.get("action") == "block":
        updates["status"] = "blocked"
        updates["result"] = None
        updates["issues"] = state.get("issues", []) + [
            {
                "source": "output",
                "action": checked.get("action"),
                "reason": "output_blocked",
                "message": checked.get("message", ""),
            }
        ]
    return updates
