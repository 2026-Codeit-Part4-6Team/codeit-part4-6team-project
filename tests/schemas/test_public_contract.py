import pytest
from pydantic import ValidationError

from backend.schemas import (
    GenerateEstimateResponse,
    GenerateRequest,
    GenerationResponse,
    GenerationUsage,
)


def test_public_basic_request_requires_platform():
    """Basic 공개 요청은 플랫폼이 필수입니다."""
    with pytest.raises(ValidationError):
        GenerateRequest(chatbot_type="basic", question="광고를 만들어줘", max_accepted_credits=0)


def test_public_basic_request_uses_xbanner_platform_enum():
    """X-배너의 공개 wire 값은 xbanner이며 기존 banner는 거부합니다."""
    request = GenerateRequest(
        chatbot_type="basic",
        question="X-배너 광고를 만들어줘",
        platform="xbanner",
        max_accepted_credits=0,
    )
    assert request.platform == "xbanner"

    with pytest.raises(ValidationError):
        GenerateRequest(
            chatbot_type="basic",
            question="X-배너 광고를 만들어줘",
            platform="banner",
            max_accepted_credits=0,
        )


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
                "platform": "xbanner",
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


def test_generation_response_serializes_basic_result_as_basic_contract():
    """Basic 응답 재직렬화에서 Consultant 필드가 섞이지 않습니다."""
    response = GenerationResponse.model_validate(
        {
            "generation_id": 1,
            "status": "done",
            "chatbot_type": "basic",
            "result": {
                "status": "ok",
                "title": "광고 제안",
                "proposals": [
                    {"copy": "a", "image_b64": None, "error": None},
                    {"copy": "b", "image_b64": None, "error": None},
                    {"copy": "c", "image_b64": None, "error": None},
                ],
                "sources": ["상권분석"],
                "tokens_used": 3,
                "suggested_chips": [],
            },
            "usage": {"plan": "free", "credits_used": 0},
        }
    )

    result = response.model_dump(mode="json", by_alias=True)["result"]
    assert result["proposals"][0]["copy"] == "a"
    assert "strategy" not in result
    assert "reasons" not in result


def test_generation_response_serializes_consultant_result_as_consultant_contract():
    """Consultant 응답 재직렬화에서 Basic 필드가 섞이지 않습니다."""
    response = GenerationResponse.model_validate(
        {
            "generation_id": 2,
            "status": "done",
            "chatbot_type": "consultant",
            "result": {
                "status": "ok",
                "title": "상권 전략",
                "strategy": {
                    "summary": "차별화가 필요합니다.",
                    "actions": [{"type": "menu", "content": "시즌 메뉴를 도입합니다."}],
                },
                "reasons": ["동일 업종 경쟁"],
                "sources": ["상권분석"],
                "tokens_used": 4,
                "suggested_chips": ["트렌드는?", "가격 전략은?", "경쟁사 리뷰는?"],
            },
            "usage": {"plan": "free", "credits_used": 0},
        }
    )

    result = response.model_dump(mode="json", by_alias=True)["result"]
    assert result["strategy"]["summary"] == "차별화가 필요합니다."
    assert result["reasons"] == ["동일 업종 경쟁"]
    assert "proposals" not in result
