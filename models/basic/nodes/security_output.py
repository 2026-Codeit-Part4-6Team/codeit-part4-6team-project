from validation.security import check_output

from ..graph.state import BasicState


def security_output_node(state: BasicState) -> dict:
    """생성된 카피 전체 텍스트에 대해 출력 보안 검사를 수행한다.
    차단 판정이면 상태를 blocked로 전환하고, 경고(민감정보 마스킹)면
    최종 응답(result.proposals)의 카피를 마스킹본으로 교체한다."""
    copies_with_text = [c for c in state["ranked_copies"] if c.get("copy")]
    generated_text = "\n".join(c["copy"] for c in copies_with_text)
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

    if checked.get("action") == "warn":
        masked_lines = checked.get("masked_text", "").split("\n")
        result = state.get("result") or {}
        proposals = result.get("proposals") or []

        new_proposals = []
        cursor = 0
        for p in proposals:
            if p.get("copy") and cursor < len(masked_lines):
                new_proposals.append({**p, "copy": masked_lines[cursor]})
                cursor += 1
            else:
                new_proposals.append(p)
        updates["result"] = {**result, "proposals": new_proposals}

    return updates
