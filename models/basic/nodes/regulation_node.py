from validation.regulation import check_regulation

from ..graph.state import BasicState

MAX_RETRY = 2


def regulation_node(state: BasicState) -> dict:
    """랭킹된 카피들을 표시광고법 등 규제 기준으로 검수한다. 통과한 카피만
    남기고, 전부 차단되면 재시도 카운트를 올리거나 한도 초과 시 blocked 처리한다."""
    ranked = state["ranked_copies"]
    valid = [c for c in ranked if c.get("copy")]
    failed = [c for c in ranked if not c.get("copy")]

    checked = [{**c, "regulation": check_regulation(c["copy"])} for c in valid]

    passed = [c for c in checked if c["regulation"]["action"] not in ("block")]
    validation = {**state.get("validation", {})}

    if not passed:
        blocked = (
            checked[0]["regulation"]
            if checked
            else {"action": "block", "reason": "no_valid_copy", "message": ""}
        )
        validation["regulation"] = blocked
        retry_count = state.get("retry_count", 0) + 1

        updates = {"validation": validation, "retry_count": retry_count}
        if retry_count >= MAX_RETRY:
            updates["status"] = "blocked"
            updates["issues"] = state.get("issues", []) + [
                {
                    "source": "regulation",
                    "action": blocked.get("action", "block"),
                    "reason": blocked.get("reason", "regulation_blocked"),
                    "message": blocked.get("message", ""),
                }
            ]
        return updates

    validation["regulation"] = {"action": "pass", "reason": "pass", "message": ""}
    return {
        "ranked_copies": passed + failed,
        "validation": validation,
    }
