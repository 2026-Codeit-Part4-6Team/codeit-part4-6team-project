import pytest
from pydantic import ValidationError

from backend.schemas import GenerateEstimateResponse, GenerateRequest, GenerationUsage


def test_public_basic_request_requires_platform():
    """Basic 공개 요청은 플랫폼이 필수입니다."""
    with pytest.raises(ValidationError):
        GenerateRequest(chatbot_type="basic", question="광고를 만들어줘", max_accepted_credits=0)


def test_public_consultant_request_requires_null_platform():
    """Consultant 공개 요청은 플랫폼을 사용하지 않습니다."""
    request = GenerateRequest(chatbot_type="consultant", question="상권을 분석해줘", max_accepted_credits=0)
    assert request.platform is None

    with pytest.raises(ValidationError):
        GenerateRequest(
            chatbot_type="consultant",
            question="상권을 분석해줘",
            platform="instagram",
            max_accepted_credits=0,
        )


def test_public_request_rejects_service_owned_fields():
    """Frontend는 사용자와 가게 정보를 직접 보낼 수 없습니다."""
    with pytest.raises(ValidationError):
        GenerateRequest.model_validate(
            {
                "chatbot_type": "basic",
                "question": "광고를 만들어줘",
                "platform": "banner",
                "max_accepted_credits": 0,
                "user_id": 1,
            }
        )


def test_estimate_and_usage_reject_negative_values():
    """과금 응답은 음수 값을 허용하지 않습니다."""
    with pytest.raises(ValidationError):
        GenerateEstimateResponse(
            is_free=False,
            free_remaining=0,
            estimated_credits=10,
            current_credits=5,
            credits_after=-5,
            requires_confirmation=True,
        )

    with pytest.raises(ValidationError):
        GenerationUsage(plan="paid", credits_used=-1)


def test_generation_response_rejects_internal_error_result():
    """기술 오류 metadata는 Public GenerationResponse.result로 노출하지 않습니다."""
    from backend.schemas import GenerationResponse

    with pytest.raises(ValidationError):
        GenerationResponse.model_validate(
            {
                "generation_id": 1,
                "status": "failed",
                "chatbot_type": "basic",
                "result": {
                    "status": "error",
                    "reason": "timeout",
                    "message": "provider timeout",
                },
                "usage": {"plan": "free", "credits_used": 0},
            }
        )
