from fastapi import APIRouter

from backend.schemas import GenerateRequest, GenerateResponse
from backend.services.generation_service import GenerationService

router = APIRouter(tags=["generation"])
generation_service = GenerationService()


@router.post("/generate", response_model=GenerateResponse)
def generate(request: GenerateRequest) -> GenerateResponse:
    """광고 콘텐츠 생성 요청을 처리합니다."""
    return generation_service.generate(request)
