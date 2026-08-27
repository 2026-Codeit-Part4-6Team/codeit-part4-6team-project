# 보안2(출력 검증) 노드 — 전민재 PM의 check_output()을 감싸는 자리
from models.consult.graph.state import ConsultState
from validation.security import check_output


def security_output(state: ConsultState) -> dict:
    """사용자에게 노출되는 전략 조각을 각각 검증해 판정을 실제 결과에 반영한다.

    summary만이 아니라 actions[].content·reasons[]도 사용자에게 그대로 노출되므로
    모두 검사한다. 조각별로 호출해야 warn의 masked_text를 원래 위치에 정확히
    되돌릴 수 있다(D-145·D-154).

    result가 아직 채워지지 않은 상태(그래프 조기 실행 등)에서도 죽지 않도록
    summary 빈 문자열 하나를 검사한다. warn은 마스킹본으로 교체하고, block은
    사용자 응답을 폐기한 뒤 즉시 종료한다.
    """
    result = state.get("result", {})
    parts = [("summary", result.get("summary", ""))]
    parts.extend(
        (f"actions[{index}]", action.get("content", ""))
        for index, action in enumerate(result.get("actions", []))
        if isinstance(action, dict)
    )
    parts.extend(
        (f"reasons[{index}]", reason)
        for index, reason in enumerate(result.get("reasons", []))
        if isinstance(reason, str)
    )

    checked = [(path, text, check_output(text)) for path, text in parts]
    updates = {
        "validation": {
            **state.get("validation", {}),
            "output": [verdict for _path, _text, verdict in checked],
        }
    }

    blocked = next(
        (verdict for _path, _text, verdict in checked if verdict.get("action") == "block"),
        None,
    )
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

    replacements = {
        path: verdict.get("masked_text", text)
        for path, text, verdict in checked
        if verdict.get("action") == "warn"
    }
    if replacements:
        actions = [
            (
                {
                    **action,
                    "content": replacements.get(
                        f"actions[{index}]", action.get("content", "")
                    ),
                }
                if isinstance(action, dict)
                else action
            )
            for index, action in enumerate(result.get("actions", []))
        ]
        reasons = [
            replacements.get(f"reasons[{index}]", reason)
            for index, reason in enumerate(result.get("reasons", []))
        ]
        updates["result"] = {
            **result,
            "summary": replacements.get("summary", result.get("summary", "")),
            "actions": actions,
            "reasons": reasons,
        }

    return updates
