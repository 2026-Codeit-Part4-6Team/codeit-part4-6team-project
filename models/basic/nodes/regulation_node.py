from validation.regulation import check_regulation

from ..config import COPY_MAX_RETRY
from ..graph.state import BasicState


def regulation_node(state: BasicState) -> dict:
    """랭킹된 카피들을 표시광고법 등 규제 기준으로 검수한다. 통과한 카피만
    남기고, 전부 차단되면 재시도 카운트를 올리거나 한도 초과 시 blocked 처리한다."""
    ranked = state["ranked_copies"]
    results = [check_regulation(c["copy"]) if c.get("copy") else None for c in ranked]

    checked = [r for r in results if r is not None]
    has_pass = any(r["action"] == "pass" for r in checked)
    validation = {**state.get("validation", {})}

    if has_pass:
        updated = []
        for c, r in zip(ranked, results):
            if r is None or r["action"] == "pass":
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
        validation["regulation"] = {
            "action": "pass",
            "reason": "pass",
            "message": "",
            "alternative": "",
        }
        return {"ranked_copies": updated, "validation": validation}

    worst = next((r for r in checked if r["action"] == "block"), None) or (
        checked[0]
        if checked
        else {
            "action": "block",
            "reason": "no_valid_copy",
            "message": "카피 생성에 실패해 규제 검사를 진행할 수 없습니다.",
        }
    )
    validation["regulation"] = worst
    retry_count = state.get("copy_retry_count", 0) + 1
    updates = {"validation": validation, "copy_retry_count": retry_count}
    if retry_count >= COPY_MAX_RETRY:
        updates["status"] = "blocked"
        updates["issues"] = state.get("issues", []) + [
            {
                "source": "regulation",
                "action": worst.get("action", "block"),
                "reason": worst.get("reason", "regulation_blocked"),
                "message": worst.get("message", ""),
            }
        ]
    return updates
