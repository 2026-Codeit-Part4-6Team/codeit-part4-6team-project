import pytest
from pydantic import ValidationError

from backend.schemas import MODEL_RESULT_ADAPTER, BlockedResult, ErrorResult


def test_reask_uses_blocked_status_and_action():
    """추가 질문은 blocked/reask 조합으로 표현합니다."""
    result = MODEL_RESULT_ADAPTER.validate_python(
        {
            "status": "blocked",
            "action": "reask",
            "reason": "insufficient_info",
            "message": "어떤 메뉴인지 알려주세요.",
        },
        chatbot_type="basic",
    )
    assert isinstance(result, BlockedResult)
    assert result.action == "reask"


def test_blocked_result_rejects_error_action():
    """기술 오류를 정책 action으로 표현하지 않습니다."""
    with pytest.raises(ValidationError):
        BlockedResult(
            status="blocked", action="error", reason="timeout", message="실패"
        )


def test_error_result_limits_reason_codes():
    """최상위 오류는 계약된 복구 코드만 허용합니다."""
    result = ErrorResult(status="error", reason="timeout", message="시간 초과")
    assert result.reason == "timeout"

    with pytest.raises(ValidationError):
        ErrorResult(status="error", reason="parse_failed", message="파싱 실패")


@pytest.mark.parametrize(
    ("action", "reason"),
    [
        ("block", "illegal_or_injection"),
        ("block", "prohibited_item"),
        ("block", "sensitive_leak"),
        ("reask", "need_clarification"),
        ("reask", "insufficient_info"),
        ("warn", "regulation_risk"),
    ],
)
def test_blocked_result_accepts_only_contract_action_reason_pairs(action, reason):
    result = BlockedResult(
        status="blocked",
        action=action,
        reason=reason,
        message="계약된 정책 응답입니다.",
    )

    assert result.action == action
    assert result.reason == reason


@pytest.mark.parametrize(
    ("action", "reason"),
    [
        ("block", "insufficient_info"),
        ("reask", "regulation_risk"),
        ("warn", "prohibited_item"),
        ("block", "content_policy"),
        ("reask", "unknown_policy_reason"),
    ],
)
def test_blocked_result_rejects_non_contract_action_reason_pairs(action, reason):
    with pytest.raises(ValidationError):
        BlockedResult(
            status="blocked",
            action=action,
            reason=reason,
            message="잘못된 정책 응답입니다.",
        )
