import json

from backend.schemas import (
    BasicModelResult,
    BasicProposal,
    ConsultantAction,
    ConsultantModelResult,
    ConsultantStrategy,
    ProposalError,
)
from backend.services.generation_service import serialize_model_result_for_storage


def make_basic_result() -> BasicModelResult:
    """이미지와 부분 실패를 포함한 Basic 결과를 생성합니다."""
    return BasicModelResult(
        status="ok",
        title="신메뉴 광고",
        proposals=[
            BasicProposal(copy="첫 번째", image_b64="base64-image"),
            BasicProposal(
                copy="두 번째",
                image_b64=None,
                error=ProposalError(
                    field="image", reason="timeout", message="이미지 생성 실패"
                ),
            ),
            BasicProposal(
                copy=None,
                image_b64=None,
                error=ProposalError(
                    field="copy", reason="parse_failed", message="카피 생성 실패"
                ),
            ),
        ],
        sources=["상권분석"],
        tokens_used=123,
    )


def test_storage_json_removes_images_without_mutating_result():
    """저장 JSON만 이미지 필드를 제거하고 원본 응답은 유지합니다."""
    result = make_basic_result()

    stored = json.loads(serialize_model_result_for_storage(result))

    assert all("image_b64" not in proposal for proposal in stored["proposals"])
    assert result.proposals[0].image_b64 == "base64-image"


def test_storage_json_keeps_basic_text_errors_and_metadata():
    """Basic 저장 JSON은 복구에 필요한 텍스트와 메타데이터를 보존합니다."""
    stored = json.loads(serialize_model_result_for_storage(make_basic_result()))

    assert stored["proposals"][0]["copy"] == "첫 번째"
    assert stored["proposals"][1]["error"]["field"] == "image"
    assert stored["sources"] == ["상권분석"]
    assert stored["tokens_used"] == 123
    assert stored["suggested_chips"] == []


def test_storage_json_keeps_consultant_payload_and_korean():
    """Consultant 저장 JSON은 전략·근거·추천 질문과 한글을 보존합니다."""
    result = ConsultantModelResult(
        status="ok",
        title="상권 전략",
        strategy=ConsultantStrategy(
            summary="직장인 고객을 공략합니다.",
            actions=[ConsultantAction(type="target", content="점심시간을 노립니다.")],
        ),
        reasons=["유동인구가 많음"],
        sources=["상권분석"],
        tokens_used=45,
        suggested_chips=["트렌드는?", "가격은?", "경쟁사는?"],
    )

    serialized = serialize_model_result_for_storage(result)
    stored = json.loads(serialized)

    assert "직장인 고객" in serialized
    assert stored["strategy"]["actions"][0]["type"] == "target"
    assert stored["reasons"] == ["유동인구가 많음"]
    assert stored["suggested_chips"] == ["트렌드는?", "가격은?", "경쟁사는?"]
