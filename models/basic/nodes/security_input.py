from validation.security import check_input

from ..graph.state import BasicState


def security_input_node(state: BasicState) -> dict:
    """사용자 질문에 대해 입력 보안 검사(프롬프트 인젝션 등)를 수행하고,
    차단 판정이면 상태를 blocked로 전환한다."""
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
