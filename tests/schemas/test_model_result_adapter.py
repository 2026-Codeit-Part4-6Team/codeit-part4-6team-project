import logging

import pytest
from pydantic import ValidationError

from backend.schemas import (
    MODEL_RESULT_ADAPTER,
    BasicModelResult,
    BlockedResult,
    ConsultantModelResult,
    ErrorResult,
)


def basic_payload() -> dict:
    return {
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
        "tokens_used": 4,
        "suggested_chips": ["트렌드는?", "가격 전략은?", "경쟁사 리뷰는?"],
    }


def test_ok_basic_uses_basic_branch_only():
    """ok 결과는 request chatbot_type=basic이면 Basic Schema 하나만 검증합니다."""
    result = MODEL_RESULT_ADAPTER.validate_python(
        basic_payload(), chatbot_type="basic"
    )

    assert isinstance(result, BasicModelResult)


def test_ok_consultant_uses_consultant_branch_only():
    """ok 결과는 request chatbot_type=consultant이면 Consultant Schema 하나만 검증합니다."""
    result = MODEL_RESULT_ADAPTER.validate_python(
        consultant_payload(), chatbot_type="consultant"
    )

    assert isinstance(result, ConsultantModelResult)


def test_blocked_and_error_dispatch_by_status():
    """blocked/error는 성공 Union 추론 없이 status로 직접 분기합니다."""
    blocked = MODEL_RESULT_ADAPTER.validate_python(
        {
            "status": "blocked",
            "action": "reask",
            "reason": "insufficient_info",
            "message": "추가 정보가 필요합니다.",
        },
        chatbot_type="consultant",
    )
    error = MODEL_RESULT_ADAPTER.validate_python(
        {"status": "error", "reason": "timeout", "message": "시간 초과"},
        chatbot_type="basic",
    )

    assert isinstance(blocked, BlockedResult)
    assert isinstance(error, ErrorResult)


def test_basic_payload_does_not_fallback_to_basic_when_consultant_was_requested():
    """Consultant 요청에서 Basic payload가 와도 다른 성공 branch로 재시도하지 않습니다."""
    with pytest.raises(ValidationError) as error:
        MODEL_RESULT_ADAPTER.validate_python(
            basic_payload(), chatbot_type="consultant"
        )

    locations = {item["loc"] for item in error.value.errors()}
    assert ("strategy",) in locations
    assert ("reasons",) in locations


def test_consultant_payload_does_not_fallback_to_consultant_when_basic_was_requested():
    """Basic 요청에서 Consultant payload가 와도 다른 성공 branch로 재시도하지 않습니다."""
    with pytest.raises(ValidationError) as error:
        MODEL_RESULT_ADAPTER.validate_python(
            consultant_payload(), chatbot_type="basic"
        )

    locations = {item["loc"] for item in error.value.errors()}
    assert ("proposals",) in locations
    assert all("strategy" not in loc for loc in locations)


def test_unknown_status_is_schema_failure():
    """알 수 없는 status는 성공 branch를 추측하지 않고 검증 실패로 처리합니다."""
    with pytest.raises(ValidationError):
        MODEL_RESULT_ADAPTER.validate_python(
            {"status": "mystery", "message": "unknown"}, chatbot_type="basic"
        )


def test_validation_failure_logs_payload_without_base64(caplog):
    """검증 실패 payload는 진단 가능하되 base64 원문은 로그에 노출하지 않습니다."""
    payload = basic_payload()
    payload["proposals"][0]["image_b64"] = "A" * 100_000
    del payload["title"]

    with (
        caplog.at_level(logging.WARNING, logger="backend.schemas"),
        pytest.raises(ValidationError),
    ):
        MODEL_RESULT_ADAPTER.validate_python(payload, chatbot_type="basic")

    warning = next(record for record in caplog.records if record.levelno == logging.WARNING)
    message = warning.getMessage()
    assert "chatbot_type=basic" in message
    assert "title" in message
    assert "image_b64 omitted" in message
    assert "A" * 400 not in message
    assert len(message) < 4_000
