import pytest
from pydantic import ValidationError

from backend.schemas import BasicModelResult, BasicProposal, ProposalError


def success_proposal() -> BasicProposal:
    """성공 Proposal을 생성합니다."""
    return BasicProposal(copy="신메뉴를 만나보세요.", image_b64="image", error=None)


def test_basic_result_requires_exactly_three_slots():
    """Basic 결과는 실패 슬롯을 포함해 항상 세 칸입니다."""
    with pytest.raises(ValidationError):
        BasicModelResult(
            status="ok",
            title="광고",
            proposals=[success_proposal()],
            tokens_used=0,
        )


def test_copy_failure_clears_copy_and_image():
    """카피 실패 슬롯은 카피와 이미지를 모두 비웁니다."""
    proposal = BasicProposal(
        copy=None,
        image_b64=None,
        error=ProposalError(
            field="copy", reason="parse_failed", message="카피 생성 실패"
        ),
    )
    assert proposal.copy is None

    with pytest.raises(ValidationError):
        BasicProposal(
            copy="잘못 남은 카피",
            image_b64=None,
            error=ProposalError(
                field="copy", reason="parse_failed", message="카피 생성 실패"
            ),
        )


def test_image_failure_keeps_copy_and_clears_image():
    """이미지 실패 슬롯은 성공 카피만 유지합니다."""
    proposal = BasicProposal(
        copy="문구는 성공",
        image_b64=None,
        error=ProposalError(
            field="image", reason="content_policy", message="이미지 생성 실패"
        ),
    )
    assert proposal.copy == "문구는 성공"

    with pytest.raises(ValidationError):
        BasicProposal(
            copy="문구는 성공",
            image_b64="남아 있는 이미지",
            error=ProposalError(
                field="image", reason="timeout", message="이미지 생성 실패"
            ),
        )


def test_success_slot_has_no_error_and_basic_has_no_chips():
    """성공 슬롯에는 오류가 없고 Basic 추천 칩은 빈 배열입니다."""
    result = BasicModelResult(
        status="ok",
        title="광고",
        proposals=[success_proposal(), success_proposal(), success_proposal()],
        sources=[],
        tokens_used=10,
    )
    assert result.suggested_chips == []
    assert result.proposals[0].model_dump(by_alias=True)["copy"] == "신메뉴를 만나보세요."

    with pytest.raises(ValidationError):
        BasicProposal(copy=None, image_b64=None, error=None)
