from validation.security import check_output

from ..graph.state import BasicState


def security_output_node(state: BasicState) -> dict:
    """생성된 카피 전체 텍스트에 대해 출력 보안 검사를 수행한다.
    차단 판정이면 상태를 blocked로 전환하고, 경고(민감정보 마스킹)면
    최종 응답(result.proposals)의 카피를 마스킹본으로 교체한다.
    카피별로 독립 검사를 진행해, 카피 내부 줄바꿈(인스타 해시태그 등)이
    있어도 마스킹 대상이 밀리지 않는다."""
    ranked_copies = state["ranked_copies"]
    checked_list = [
        check_output(c["copy"]) if c.get("copy") else None for c in ranked_copies
    ]
    validation = {
        **state.get("validation", {}),
        "output": [c for c in checked_list if c is not None],
    }

    updates = {"validation": validation}

    blocked = next((c for c in checked_list if c and c.get("action") == "block"), None)

    if blocked:
        updates["status"] = "blocked"
        updates["result"] = None
        updates["issues"] = state.get("issues", []) + [
            {
                "source": "output",
                "action": "block",
                "reason": "output_blocked",
                "message": blocked.get("message", ""),
            }
        ]
        return updates

    if any(c and c.get("action") == "warn" for c in checked_list):
        result = state.get("result") or {}
        proposals = result.get("proposals") or []
        new_proposals = [
            (
                {**p, "copy": checked_list[i].get("masked_text", p.get("copy"))}
                if i < len(checked_list)
                and checked_list[i]
                and checked_list[i].get("action") == "warn"
                else p
            )
            for i, p in enumerate(proposals)
        ]
        updates["result"] = {**result, "proposals": new_proposals}

    return updates
