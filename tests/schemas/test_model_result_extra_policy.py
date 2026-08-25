import logging

import pytest
from pydantic import ValidationError

from backend.schemas import (
    MODEL_RESULT_ADAPTER,
    BasicModelResult,
    BlockedResult,
    ConsultantAction,
    ConsultantModelResult,
    ErrorResult,
    GenerateRequest,
    InboundModel,
    ProposalError,
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


def test_model_results_share_inbound_base():
    """Model→Service 최상위 결과만 공통 inbound 완화 정책을 사용합니다."""
    assert issubclass(BasicModelResult, InboundModel)
    assert issubclass(ConsultantModelResult, InboundModel)
    assert issubclass(BlockedResult, InboundModel)
    assert issubclass(ErrorResult, InboundModel)


def test_inbound_model_logs_ignored_field_name_without_value(caplog):
    """무시한 키 이름은 관측하되 모델 진단값은 로그에 노출하지 않습니다."""
    payload = {**basic_payload(), "debug_trace": "secret-diagnostic-value"}

    with caplog.at_level(logging.INFO, logger="backend.schemas"):
        MODEL_RESULT_ADAPTER.validate_python(payload, chatbot_type="basic")

    matching_records = [
        record for record in caplog.records if "debug_trace" in record.getMessage()
    ]
    assert len(matching_records) == 1
    assert "secret-diagnostic-value" not in caplog.text


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


@pytest.mark.parametrize(
    ("model", "payload"),
    [
        (
            ProposalError,
            {
                "field": "copy",
                "reason": "timeout",
                "message": "생성 실패",
                "debug_trace": "nested-debug",
            },
        ),
        (
            ConsultantAction,
            {
                "type": "menu",
                "content": "시즌 메뉴를 도입합니다.",
                "debug_trace": "nested-debug",
            },
        ),
    ],
)
def test_nested_leaf_models_reject_unknown_fields(model, payload):
    """ProposalError와 ConsultantAction까지 중첩 strict 경계를 유지합니다."""
    with pytest.raises(ValidationError):
        model.model_validate(payload)


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
