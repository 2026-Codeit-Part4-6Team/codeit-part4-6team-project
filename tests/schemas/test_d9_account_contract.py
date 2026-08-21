from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from backend.schemas import (
    GenerationDetailResponse,
    GenerationListItem,
    UserSummaryResponse,
)

NOW = datetime(2026, 8, 21, tzinfo=UTC)


def list_payload():
    return {
        "id": 1,
        "chatbot_type": "basic",
        "title": None,
        "question": "광고를 만들어줘",
        "platform": "instagram",
        "plan": "free",
        "credits_used": 0,
        "tokens_used": 3,
        "status": "done",
        "created_at": NOW,
    }


def test_user_summary_requires_nonnegative_server_counts():
    summary = UserSummaryResponse(
        credits=100,
        daily_free_remaining=9,
        total_generations=3,
        published_generations=1,
    )
    assert summary.total_generations == 3

    with pytest.raises(ValidationError):
        UserSummaryResponse(
            credits=100,
            daily_free_remaining=-1,
            total_generations=3,
            published_generations=1,
        )


def test_generation_history_contract_rejects_internal_fields():
    with pytest.raises(ValidationError):
        GenerationListItem(**list_payload(), request_hash="secret")

    with pytest.raises(ValidationError):
        GenerationListItem(**list_payload(), idempotency_key="secret")


def test_generation_detail_exposes_only_public_result_and_final_fields():
    detail = GenerationDetailResponse(
        **list_payload(),
        source_gen_id=None,
        result=None,
        copy_content="최종 문구",
        image_b64=None,
        selected_proposal_index=1,
        hitl_approved=True,
    )

    assert detail.selected_proposal_index == 1
    assert "request_hash" not in detail.model_dump()

    with pytest.raises(ValidationError):
        GenerationDetailResponse(
            **list_payload(),
            source_gen_id=None,
            result=None,
            copy_content="최종 문구",
            image_b64=None,
            selected_proposal_index=3,
            hitl_approved=True,
        )
