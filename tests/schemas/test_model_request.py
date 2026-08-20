import pytest
from pydantic import ValidationError

from backend.schemas import GenerateExtra, GenerateRequest, ModelRequest, StoreContext


def make_store() -> StoreContext:
    """필수 가게 Context를 생성합니다."""
    return StoreContext(
        name="카페 코드잇",
        type="카페",
        address="서울 강남구 역삼동",
        lat=37.5,
        lng=127.0,
    )


def test_generate_extra_accepts_only_five_contract_fields():
    """추가 입력은 계약된 다섯 필드만 허용합니다."""
    extra = GenerateExtra(
        purpose="신메뉴 출시",
        price_range="5000-8000",
        target_age="20-30대",
        strength="직접 로스팅",
        clarification="아이스 아메리카노예요",
    )
    assert extra.clarification == "아이스 아메리카노예요"

    with pytest.raises(ValidationError):
        GenerateExtra.model_validate({"unknown": "value"})


def test_model_request_applies_platform_policy():
    """모델 요청도 챗봇별 플랫폼 정책을 검증합니다."""
    basic = ModelRequest(
        chatbot_type="basic",
        user_id=1,
        question="광고를 만들어줘",
        platform="instagram",
        store=make_store(),
    )
    consultant = ModelRequest(
        chatbot_type="consultant",
        user_id=1,
        question="상권을 분석해줘",
        store=make_store(),
    )
    assert basic.platform == "instagram"
    assert consultant.platform is None

    with pytest.raises(ValidationError):
        ModelRequest(
            chatbot_type="basic",
            user_id=1,
            question="광고를 만들어줘",
            store=make_store(),
        )


def test_store_context_requires_coordinates():
    """가게 Context는 두 모델이 공유할 좌표를 필수로 가집니다."""
    with pytest.raises(ValidationError):
        StoreContext.model_validate(
            {"name": "카페", "type": "카페", "address": "서울 강남구"}
        )


def test_model_request_accepts_server_owned_consultant_source_context():
    """Consultant 결과 연계 Context는 Service→Model 요청에서만 허용합니다."""
    request = ModelRequest.model_validate(
        {
            "chatbot_type": "basic",
            "user_id": 1,
            "question": "이 전략으로 광고를 만들어줘",
            "platform": "instagram",
            "store": make_store().model_dump(),
            "source_context": {
                "generation_id": 7,
                "strategy": {
                    "summary": "점심 시간대 직장인 타깃",
                    "actions": [
                        {"type": "target", "content": "직장인 메시지를 강화합니다."}
                    ],
                },
                "reasons": ["오피스 상권"],
                "sources": ["Mock 상권분석"],
            },
        }
    )

    assert request.source_context is not None
    assert request.source_context.generation_id == 7
    assert request.source_context.strategy.summary == "점심 시간대 직장인 타깃"


def test_generate_request_rejects_server_owned_source_context():
    """Frontend body는 서버가 구성해야 하는 Consultant Context를 주입할 수 없습니다."""
    with pytest.raises(ValidationError):
        GenerateRequest.model_validate(
            {
                "chatbot_type": "basic",
                "question": "광고를 만들어줘",
                "platform": "instagram",
                "max_accepted_credits": 0,
                "source_context": {
                    "generation_id": 7,
                    "strategy": {
                        "summary": "주입 금지",
                        "actions": [{"type": "other", "content": "금지"}],
                    },
                    "reasons": ["금지"],
                    "sources": ["금지"],
                },
            }
        )
