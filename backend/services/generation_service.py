from uuid import uuid4

from backend.schemas import GenerateRequest, GenerateResponse, GenerationResult


class GenerationService:
    """광고 콘텐츠 생성 유스케이스를 조율합니다."""

    def generate(self, request: GenerateRequest) -> GenerateResponse:
        """초기 연동 검증을 위한 목 생성 결과를 반환합니다."""
        return GenerateResponse(
            request_id=str(uuid4()),
            status="completed",
            result=GenerationResult(
                text=f"광고 콘텐츠 생성 요청을 확인했습니다: {request.prompt}"
            ),
        )
