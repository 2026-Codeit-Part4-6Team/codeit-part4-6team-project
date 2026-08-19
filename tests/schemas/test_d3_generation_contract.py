import pytest
from pydantic import ValidationError

from backend.schemas import GenerateEstimateRequest, GenerateRequest


def test_estimate_request_does_not_accept_billing_consent():
    with pytest.raises(ValidationError):
        GenerateEstimateRequest(
            chatbot_type="basic",
            question="광고 만들어줘",
            platform="instagram",
            max_accepted_credits=50,
        )


def test_generate_request_requires_nonnegative_billing_consent():
    request = GenerateRequest(
        chatbot_type="basic",
        question="광고 만들어줘",
        platform="instagram",
        max_accepted_credits=50,
    )
    assert request.max_accepted_credits == 50

    with pytest.raises(ValidationError):
        GenerateRequest(
            chatbot_type="basic",
            question="광고 만들어줘",
            platform="instagram",
        )

    with pytest.raises(ValidationError):
        GenerateRequest(
            chatbot_type="basic",
            question="광고 만들어줘",
            platform="instagram",
            max_accepted_credits=-1,
        )
