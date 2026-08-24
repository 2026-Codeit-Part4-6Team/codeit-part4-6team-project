from validation.regulation import check_regulation

from ..config import COPY_MAX_RETRY
from ..graph.state import BasicState


def regulation_node(state: BasicState) -> dict:
    """랭킹된 카피들을 표시광고법 등 규제 기준으로 검수한다(§6.2).

    pass 카피가 하나라도 있으면 그것만 남기고 통과시킨다(block 카피만 제외,
    기존 동작 유지). pass가 하나도 없고 warn만 있으면 카피 전체를 재생성한다
    (상한 COPY_MAX_RETRY 공유). 상한을 넘기면 대안 문구를 담아
    blocked(action=warn)로 종료한다 — 이 시점부터 크레딧 롤백 대상이다.
    전부 block이어도 같은 재시도 루프를 타고, 상한 초과 시 action=block으로 종료한다.
    """
    ranked = state["ranked_copies"]
    results = [check_regulation(c["copy"]) if c.get("copy") else None for c in ranked]
    checked = [r for r in results if r is not None]

    validation = {**state.get("validation", {})}
    has_pass = any(r["action"] == "pass" for r in checked)

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

    # pass가 하나도 없다 — warn만 있거나 block만 있거나 섞여 있다.
    # block이 하나라도 있으면 그걸 대표로, 없으면(=전부 warn) 첫 결과를 대표로 삼는다.
    worst = next((r for r in checked if r["action"] == "block"), None) or (
        checked[0]
        if checked
        else {
            "action": "block",
            "reason": "no_valid_copy",
            "message": "카피 생성에 실패해 규제 검사를 진행할 수 없습니다.",
            "alternative": "",
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
