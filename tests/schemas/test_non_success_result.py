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
        }
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
