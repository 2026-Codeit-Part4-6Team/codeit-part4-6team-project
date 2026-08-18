# models/consult/tests/test_assemble_response.py
"""조립 결과가 서비스 스키마를 실제로 통과하는지 확인한다.

주의: backend import는 이 테스트 파일에서만 한다 — 프로덕션 코드가 backend를
import하면 배포 단위 분리(D-031)가 깨진다.
"""
import pytest
from pydantic import ValidationError

from backend.schemas import (
    MODEL_RESULT_ADAPTER,
    BlockedResult,
    ConsultantModelResult,
    ErrorResult,
)
from models.consult.main import assemble_response

_STORE = {"name": "카페 코드잇", "type": "카페", "address": "서울 강남구 역삼동",
          "lat": 37.4979, "lng": 127.0276}


def _ok_state(**overrides) -> dict:
    base = {
        "store": _STORE,
        "result": {
            "title": "역삼동 카페 여름 전략",
            "summary": "반경 500m 동일 업종 177곳으로 경쟁이 치열합니다.",
            "actions": [{"type": "menu", "content": "아이스 커피 신메뉴를 출시하세요."}],
            "reasons": ["반경 500m 내 동일 업종 177곳"],
        },
        "sources": ["상권분석", "트렌드"],
        "tokens_used": 1124,
        "suggested_chips": ["트렌드는요?", "가격 전략은요?", "경쟁사 리뷰는요?"],
    }
    return {**base, **overrides}


def test_ok_state_passes_service_contract():
    """정상 ok 상태는 ConsultantModelResult 검증을 통과해야 한다."""
    result = MODEL_RESULT_ADAPTER.validate_python(
        assemble_response(_ok_state()), chatbot_type="consultant"
    )
    assert isinstance(result, ConsultantModelResult)
    assert result.strategy.summary.startswith("반경")
    assert result.reasons == ["반경 500m 내 동일 업종 177곳"]


def test_missing_title_falls_back_instead_of_failing():
    """title이 없어도 전략을 버리지 않고 폴백한다(D-179)."""
    state = _ok_state()
    state["result"].pop("title")

    response = assemble_response(state)

    assert response["title"] == "카페 코드잇 마케팅 전략"
    MODEL_RESULT_ADAPTER.validate_python(response, chatbot_type="consultant")


def test_empty_sources_falls_back_to_store_info():
    """상권·트렌드 둘 다 실패해도 sources 최소 1개 계약을 지킨다(D6)."""
    response = assemble_response(_ok_state(sources=[]))
    assert response["sources"] == ["가게정보"]
    MODEL_RESULT_ADAPTER.validate_python(response, chatbot_type="consultant")


@pytest.mark.parametrize("chips", [[], ["하나만"], ["a", "b", "c", "d"], ["", "", ""]])
def test_invalid_chips_fall_back_to_exactly_three(chips):
    """칩 개수·빈 문자열 오류는 고정 질문 3개로 폴백한다."""
    response = assemble_response(_ok_state(suggested_chips=chips))
    assert len(response["suggested_chips"]) == 3
    MODEL_RESULT_ADAPTER.validate_python(response, chatbot_type="consultant")


def test_blocked_state_becomes_blocked_result():
    """차단 상태는 BlockedResult 형태으로 조립된다."""
    state = {
        "status": "blocked",
        "issues": [{"source": "input", "action": "block",
                    "reason": "illegal_or_injection",
                    "message": "불법 키워드가 포함되어 있습니다."}],
    }
    result = MODEL_RESULT_ADAPTER.validate_python(
        assemble_response(state), chatbot_type="consultant"
    )
    assert isinstance(result, BlockedResult)
    assert result.action == "block"


def test_error_reason_stays_inside_contract_enum():
    """ErrorResult.reason은 계약 enum 4종을 벗어나면 안 된다."""
    state = {
        "status": "error",
        "issues": [{"source": "self_check", "reason": "unknown", "message": "근거 부족"}],
    }
    result = MODEL_RESULT_ADAPTER.validate_python(
        assemble_response(state), chatbot_type="consultant"
    )
    assert isinstance(result, ErrorResult)


def test_error_reason_outside_enum_is_normalized_to_unknown():
    """issues의 reason이 계약 enum 4종 밖이면 그대로 흘려보내지 않고 unknown으로
    정규화한다 — 그대로 두면 서비스 쪽 ErrorResult 검증에서 그냥 실패한다(Codex 리뷰)."""
    state = {
        "status": "error",
        "issues": [{"source": "self_check", "reason": "self_check_failed", "message": "실패"}],
    }
    response = assemble_response(state)

    assert response["reason"] == "unknown"
    MODEL_RESULT_ADAPTER.validate_python(response, chatbot_type="consultant")


def test_whitespace_only_title_falls_back_instead_of_passing_through():
    """title이 공백뿐이어도 그대로 통과시키지 않는다 — strategy.py의 title 검증
    (타입+strip)과 조립 단계 검증 수준이 달랐던 문제(Codex 리뷰)."""
    response = assemble_response(_ok_state(result={**_ok_state()["result"], "title": "   "}))

    assert response["title"] == "카페 코드잇 마케팅 전략"


def test_fallback_chips_are_not_the_shared_list_object():
    """폴백 칩 리스트를 그대로 반환하면, 호출한 쪽이 리스트를 변형했을 때 이후 모든
    폴백 응답이 오염된다(Codex 리뷰) — 매번 새 리스트를 반환해야 한다."""
    response = assemble_response(_ok_state(suggested_chips=[]))
    response["suggested_chips"].append("오염")

    second_response = assemble_response(_ok_state(suggested_chips=[]))

    assert "오염" not in second_response["suggested_chips"]


def test_empty_result_is_converted_to_error_not_ok():
    """전략이 비었는데 ok로 내보내면 계약이 깨진다."""
    response = assemble_response({"store": _STORE, "result": {}})
    assert response["status"] == "error"
    with pytest.raises(ValidationError):
        ConsultantModelResult.model_validate(response)
