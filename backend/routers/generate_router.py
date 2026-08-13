from fastapi import APIRouter

from backend.schemas import PreviewGenerateRequest, PreviewGenerateResponse
from backend.services.generation_service import GenerationService

router = APIRouter(tags=["generation"])
generation_service = GenerationService()


@router.post("/generate", response_model=PreviewGenerateResponse)
def generate(request: PreviewGenerateRequest) -> PreviewGenerateResponse:
    """광고 콘텐츠 생성 요청을 처리합니다."""
    return generation_service.generate(request)
