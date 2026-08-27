# models/consult/nodes/security_output.py 테스트
from unittest.mock import patch

from models.consult.nodes.security_output import security_output

_STORE = {
    "name": "카페 코드잇",
    "type": "카페",
    "address": "서울 강남구 역삼동",
    "lat": 37.5,
    "lng": 127.0,
}


def _state(
    summary: str | None = "전략 요약",
    actions: list[dict] | None = None,
    reasons: list[str] | None = None,
) -> dict:
    state = {
        "chatbot_type": "consultant",
        "user_id": 1,
        "question": "질문",
        "store": _STORE,
    }
    if summary is not None:
        state["result"] = {
            "summary": summary,
            "actions": actions or [],
            "reasons": reasons or [],
        }
    return state


@patch("models.consult.nodes.security_output.check_output")
def test_calls_check_output_with_result_summary(mock_check_output) -> None:
    mock_check_output.return_value = {"action": "pass", "message": ""}

    security_output(_state("전략 요약 텍스트"))

    mock_check_output.assert_called_once_with("전략 요약 텍스트")


@patch("models.consult.nodes.security_output.check_output")
def test_stores_result_under_validation_output(mock_check_output) -> None:
    mock_check_output.return_value = {"action": "warn", "message": "표현 주의"}

    result = security_output(_state())

    assert result == {"validation": {"output": {"action": "warn", "message": "표현 주의"}}}


@patch("models.consult.nodes.security_output.check_output")
def test_combines_summary_actions_and_reasons_for_validation(mock_check_output) -> None:
    """actions[].content·reasons[]도 사용자에게 그대로 노출되므로 summary만이 아니라
    셋을 합쳐서 check_output()에 넘긴다(PM 리뷰, PR #93)."""
    mock_check_output.return_value = {"action": "pass", "message": ""}
    state = _state(
        summary="전략 요약",
        actions=[{"type": "menu", "content": "액션 내용"}],
        reasons=["근거 문장"],
    )

    security_output(state)

    validated_text = mock_check_output.call_args.args[0]
    assert "전략 요약" in validated_text
    assert "액션 내용" in validated_text
    assert "근거 문장" in validated_text


@patch("models.consult.nodes.security_output.check_output")
def test_handles_missing_result_gracefully(mock_check_output) -> None:
    """아직 전략 노드가 result를 채우지 않은 상태(그래프 조기 실행 등)에서도 빈 문자열로 안전하게 호출한다."""
    mock_check_output.return_value = {"action": "pass", "message": ""}
    state = _state(summary=None)
    assert "result" not in state

    security_output(state)

    mock_check_output.assert_called_once_with("")
