from backend.schemas import (
    BasicModelResult,
    BasicProposal,
    ConsultantAction,
    ConsultantModelResult,
    ConsultantStrategy,
    ModelRequest,
)


class MockBasicChatbotClient:
    """기본 챗봇 계약을 재현하는 고정 응답 Client."""

    async def generate(self, request: ModelRequest) -> BasicModelResult:
        """Basic 요청에 세 개의 고정 Proposal을 반환합니다."""
        if request.chatbot_type != "basic":
            raise ValueError("MockBasicChatbotClient의 chatbot_type은 basic이어야 합니다.")

        proposals = [
            BasicProposal(copy=f"{request.store.name}의 매력을 지금 만나보세요.", image_b64=None),
            BasicProposal(copy="오늘만의 특별한 메뉴를 소개합니다.", image_b64=None),
            BasicProposal(copy="가까운 일상에 새로운 즐거움을 더해보세요.", image_b64=None),
        ]
        return BasicModelResult(
            status="ok",
            title=f"{request.store.name} 광고 제안",
            proposals=proposals,
            sources=["Mock 상권분석", "Mock 트렌드"],
            tokens_used=0,
        )


class MockConsultantChatbotClient:
    """컨설턴트 챗봇 계약을 재현하는 고정 응답 Client."""

    async def generate(self, request: ModelRequest) -> ConsultantModelResult:
        """Consultant 요청에 전략과 추천 질문을 반환합니다."""
        if request.chatbot_type != "consultant":
            raise ValueError(
                "MockConsultantChatbotClient의 chatbot_type은 consultant여야 합니다."
            )

        return ConsultantModelResult(
            status="ok",
            title=f"{request.store.name} 마케팅 전략",
            strategy=ConsultantStrategy(
                summary="주변 경쟁 환경을 고려한 차별화가 필요합니다.",
                actions=[
                    ConsultantAction(type="menu", content="시즌 한정 메뉴를 도입합니다."),
                    ConsultantAction(
                        type="promotion", content="첫 방문 고객 프로모션을 운영합니다."
                    ),
                    ConsultantAction(
                        type="target", content="핵심 고객층에 맞춘 메시지를 사용합니다."
                    ),
                ],
            ),
            reasons=["주변 동일 업종 경쟁", "시즌 메뉴 관심 증가"],
            sources=["Mock 상권분석", "Mock 트렌드"],
            tokens_used=0,
            suggested_chips=[
                "주변 트렌드는 어때요?",
                "가격 전략도 알려주세요",
                "경쟁사 리뷰는요?",
            ],
        )
