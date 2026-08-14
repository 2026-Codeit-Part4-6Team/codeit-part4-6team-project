import pytest
from pydantic import ValidationError

from backend.schemas import (
    BasicModelResult,
    BlockedResult,
    ConsultantModelResult,
    ErrorResult,
    GenerateRequest,
)


def basic_payload() -> dict:
    return {
        "status": "ok",
        "title": "광고 제안",
        "proposals": [
            {"copy": "첫 번째 카피", "image_b64": None, "error": None},
            {"copy": "두 번째 카피", "image_b64": None, "error": None},
            {"copy": "세 번째 카피", "image_b64": None, "error": None},
        ],
        "sources": ["상권분석"],
        "tokens_used": 10,
        "suggested_chips": [],
    }


def consultant_payload() -> dict:
    return {
        "status": "ok",
        "title": "상권 전략",
        "strategy": {
            "summary": "차별화가 필요합니다.",
            "actions": [{"type": "menu", "content": "시즌 메뉴를 도입합니다."}],
        },
        "reasons": ["동일 업종 경쟁"],
        "sources": ["상권분석"],
        "tokens_used": 10,
        "suggested_chips": ["트렌드는?", "가격 전략은?", "경쟁사 리뷰는?"],
    }


@pytest.mark.parametrize(
    ("model", "payload"),
    [
        (BasicModelResult, basic_payload()),
        (ConsultantModelResult, consultant_payload()),
        (
            BlockedResult,
            {
                "status": "blocked",
                "action": "reask",
                "reason": "insufficient_info",
                "message": "추가 정보가 필요합니다.",
            },
        ),
        (
            ErrorResult,
            {
                "status": "error",
                "reason": "timeout",
                "message": "시간 초과",
            },
        ),
    ],
)
def test_model_result_top_level_ignores_unknown_fields(model, payload):
    """Model→Service 결과는 서비스가 쓰지 않는 최상위 필드를 무시합니다."""
    result = model.model_validate({**payload, "debug_trace": "model-debug"})

    assert "debug_trace" not in result.model_dump()


def test_nested_model_result_objects_still_reject_unknown_fields():
    """결과 최상위만 완화하고 Proposal/Strategy 내부 구조는 strict를 유지합니다."""
    payload = basic_payload()
    payload["proposals"][0]["debug_trace"] = "nested-debug"

    with pytest.raises(ValidationError):
        BasicModelResult.model_validate(payload)

    consultant = consultant_payload()
    consultant["strategy"]["debug_trace"] = "nested-debug"

    with pytest.raises(ValidationError):
        ConsultantModelResult.model_validate(consultant)


def test_frontend_request_still_rejects_unknown_fields():
    """Frontend→Service 공개 요청의 extra=forbid 정책은 유지합니다."""
    with pytest.raises(ValidationError):
        GenerateRequest.model_validate(
            {
                "chatbot_type": "basic",
                "question": "광고를 만들어줘",
                "platform": "instagram",
                "debug_trace": "frontend-debug",
            }
        )
