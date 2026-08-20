from validation.regulation import check_regulation

from ..config import COPY_MAX_RETRY
from ..graph.state import BasicState


def regulation_node(state: BasicState) -> dict:
    """랭킹된 카피들을 표시광고법 등 규제 기준으로 검수한다. 통과한 카피만
    남기고, 전부 차단되면 재시도 카운트를 올리거나 한도 초과 시 blocked 처리한다."""
    ranked = state["ranked_copies"]
    results = [check_regulation(c["copy"]) if c.get("copy") else None for c in ranked]

    passed_exists = any(r is not None and r["action"] != "block" for r in results)
    validation = {**state.get("validation", {})}

    if not passed_exists:
        blocked = next((r for r in results if r is not None), None) or {
            "action": "block",
            "reason": "no_valid_copy",
            "message": "",
        }
        validation["regulation"] = blocked
        retry_count = state.get("copy_retry_count", 0) + 1

        updates = {"validation": validation, "copy_retry_count": retry_count}
        if retry_count >= COPY_MAX_RETRY:
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

    updated = []
    for c, r in zip(ranked, results):
        if r is None or r["action"] != "block":
            updated.append(c)
        else:
            updated.append(
                {
                    "copy": None,
                    "image_b64": None,
                    "error": {
                        "field": "copy",
                        "reason": "content_policy",
                        "message": r.get("message", ""),
                    },
                }
            )

    validation["regulation"] = {"action": "pass", "reason": "pass", "message": ""}
    return {"ranked_copies": updated, "validation": validation}