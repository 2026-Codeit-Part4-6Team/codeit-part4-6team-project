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
    mock_check_output.return_value = {
        "action": "pass",
        "message": "",
        "masked_text": "전략 요약 텍스트",
    }

    security_output(_state("전략 요약 텍스트"))

    mock_check_output.assert_called_once_with("전략 요약 텍스트")


@patch("models.consult.nodes.security_output.check_output")
def test_stores_result_under_validation_output(mock_check_output) -> None:
    mock_check_output.return_value = {
        "action": "warn",
        "message": "표현 주의",
        "masked_text": "전략 요약",
    }

    result = security_output(_state())

    assert result["validation"] == {
        "output": [
            {"action": "warn", "message": "표현 주의", "masked_text": "전략 요약"}
        ]
    }


@patch("models.consult.nodes.security_output.check_output")
def test_checks_summary_actions_and_reasons_independently(mock_check_output) -> None:
    """각 조각을 따로 검사해야 warn의 masked_text를 원래 필드에 되돌릴 수 있다."""
    mock_check_output.side_effect = lambda text: {
        "action": "pass",
        "message": "",
        "masked_text": text,
    }
    state = _state(
        summary="전략 요약",
        actions=[{"type": "menu", "content": "액션 내용"}],
        reasons=["근거 문장"],
    )

    security_output(state)

    assert [call.args[0] for call in mock_check_output.call_args_list] == [
        "전략 요약",
        "액션 내용",
        "근거 문장",
    ]


@patch("models.consult.nodes.security_output.check_output")
def test_warn_replaces_each_result_field_with_masked_text(mock_check_output) -> None:
    mock_check_output.side_effect = [
        {"action": "warn", "message": "마스킹", "masked_text": "요약 ***"},
        {"action": "warn", "message": "마스킹", "masked_text": "액션 ***"},
        {"action": "warn", "message": "마스킹", "masked_text": "근거 ***"},
    ]
    state = _state(
        summary="요약 010-1234-5678",
        actions=[{"type": "promotion", "content": "액션 010-1234-5678"}],
        reasons=["근거 010-1234-5678"],
    )

    result = security_output(state)

    assert result["result"] == {
        "summary": "요약 ***",
        "actions": [{"type": "promotion", "content": "액션 ***"}],
        "reasons": ["근거 ***"],
    }


@patch("models.consult.nodes.security_output.check_output")
def test_block_stops_pipeline_and_discards_result(mock_check_output) -> None:
    mock_check_output.return_value = {
        "action": "block",
        "message": "내부 정보가 포함됐습니다.",
        "masked_text": "",
    }

    result = security_output(_state())

    assert result["status"] == "blocked"
    assert result["result"] is None
    assert result["issues"] == [
        {
            "source": "output",
            "action": "block",
            "reason": "output_blocked",
            "message": "내부 정보가 포함됐습니다.",
        }
    ]


@patch("models.consult.nodes.security_output.check_output")
def test_handles_missing_result_gracefully(mock_check_output) -> None:
    """아직 전략 노드가 result를 채우지 않은 상태(그래프 조기 실행 등)에서도 빈 문자열로 안전하게 호출한다."""
    mock_check_output.return_value = {"action": "pass", "message": "", "masked_text": ""}
    state = _state(summary=None)
    assert "result" not in state

    security_output(state)

    mock_check_output.assert_called_once_with("")
