import pytest
from pydantic import ValidationError

from backend.schemas import (
    ConsultantAction,
    ConsultantModelResult,
    ConsultantStrategy,
)


def make_strategy() -> ConsultantStrategy:
    """최소 Consultant 전략을 생성합니다."""
    return ConsultantStrategy(
        summary="경쟁이 치열합니다.",
        actions=[ConsultantAction(type="menu", content="시즌 메뉴를 도입합니다.")],
    )


def test_consultant_result_requires_three_chips_and_sources():
    """Consultant 성공 결과는 근거와 추천 질문 세 개가 필수입니다."""
    result = ConsultantModelResult(
        status="ok",
        title="상권 전략",
        strategy=make_strategy(),
        reasons=["동일 업종 12곳"],
        sources=["상권분석"],
        tokens_used=10,
        suggested_chips=["트렌드는?", "가격 전략은?", "경쟁사 리뷰는?"],
    )
    assert len(result.suggested_chips) == 3

    with pytest.raises(ValidationError):
        ConsultantModelResult(
            status="ok",
            title="상권 전략",
            strategy=make_strategy(),
            reasons=["동일 업종 12곳"],
            sources=["상권분석"],
            tokens_used=10,
            suggested_chips=["하나만"],
        )


def test_consultant_action_type_is_limited():
    """Consultant action은 계약된 네 종류만 허용합니다."""
    with pytest.raises(ValidationError):
        ConsultantAction(type="price", content="가격을 낮춥니다.")


def test_consultant_result_rejects_basic_payload():
    """Basic 성공 payload 전체를 Consultant 결과로 오인하지 않습니다."""
    with pytest.raises(ValidationError) as exc_info:
        ConsultantModelResult.model_validate(
            {
                "status": "ok",
                "title": "광고 제안",
                "proposals": [
                    {"copy": "a", "image_b64": None, "error": None},
                    {"copy": "b", "image_b64": None, "error": None},
                    {"copy": "c", "image_b64": None, "error": None},
                ],
                "sources": ["상권분석"],
                "tokens_used": 1,
                "suggested_chips": [],
            }
        )

    missing = {
        error["loc"][0]
        for error in exc_info.value.errors()
        if error["type"] == "missing"
    }
    assert {"strategy", "reasons"} <= missing
