def assemble_response(state):
    """파이프라인 최종 상태를 API 응답 형식(ok/error/blocked)으로 변환한다."""
    if state["status"] == "ok":
        return {
            "status": "ok",
            **state.get("result", {}),
            "sources": state.get("sources"),
            "tokens_used": state.get("tokens_used", 0),
        }

    if state["status"] == "error":
        last_issue = (state.get("issues") or [{}])[-1]
        return {
            "status": "error",
            "message": last_issue.get("message", "모델 처리 중 오류가 발생했습니다."),
        }

    # blocked
    last_issue = (state.get("issues") or [{}])[-1]
    return {
        "status": "blocked",
        "action": last_issue.get("action"),
        "reason": last_issue.get("reason"),
        "message": last_issue.get("message"),
    }
