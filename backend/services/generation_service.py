import json
from uuid import uuid4

from backend.schemas import (
    BasicModelResult,
    ConsultantModelResult,
    PreviewGenerateRequest,
    PreviewGenerateResponse,
    PreviewGenerationResult,
)


def serialize_model_result_for_storage(
    result: BasicModelResult | ConsultantModelResult,
) -> str:
    """모델 성공 결과를 이미지 없이 DB 저장용 JSON으로 직렬화합니다."""
    payload = result.model_dump(mode="json", by_alias=True)
    if isinstance(result, BasicModelResult):
        for proposal in payload["proposals"]:
            proposal.pop("image_b64", None)
    return json.dumps(payload, ensure_ascii=False)


class GenerationService:
    """광고 콘텐츠 생성 유스케이스를 조율합니다."""

    def generate(self, request: PreviewGenerateRequest) -> PreviewGenerateResponse:
        """초기 연동 검증을 위한 목 생성 결과를 반환합니다."""
        return PreviewGenerateResponse(
            request_id=str(uuid4()),
            status="completed",
            result=PreviewGenerationResult(
                text=f"광고 콘텐츠 생성 요청을 확인했습니다: {request.prompt}"
            ),
        )
