import pytest
from pydantic import ValidationError

from backend.schemas import PublishRequest, PublishResponse, WaitingCopyResponse


def test_publish_request_accepts_only_three_proposal_slots():
    assert PublishRequest(proposal_index=0, image_b64=None).proposal_index == 0
    assert PublishRequest(proposal_index=2, image_b64="encoded").proposal_index == 2

    with pytest.raises(ValidationError):
        PublishRequest(proposal_index=3, image_b64=None)


def test_publish_response_requires_published_approval():
    response = PublishResponse(
        generation_id=7,
        status="published",
        hitl_approved=True,
        proposal_index=1,
    )

    assert response.model_dump() == {
        "generation_id": 7,
        "status": "published",
        "hitl_approved": True,
        "proposal_index": 1,
    }

    with pytest.raises(ValidationError):
        PublishResponse(
            generation_id=7,
            status="done",
            hitl_approved=True,
            proposal_index=1,
        )


def test_waiting_copy_response_is_strict():
    value = WaitingCopyResponse(id=1, copy_text="광고를 준비하고 있어요.", industry=None)
    assert value.copy_text == "광고를 준비하고 있어요."

    with pytest.raises(ValidationError):
        WaitingCopyResponse(
            id=1,
            copy_text="광고를 준비하고 있어요.",
            industry=None,
            ignored=True,
        )
