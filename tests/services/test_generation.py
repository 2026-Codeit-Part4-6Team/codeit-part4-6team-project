from uuid import UUID

from backend.schemas import PreviewGenerateRequest
from backend.services.generation_service import GenerationService


def test_generation_service_returns_mock_result() -> None:
    service = GenerationService()

    response = service.generate(PreviewGenerateRequest(prompt="여름 메뉴"))

    assert UUID(response.request_id)
    assert response.status == "completed"
    assert "여름 메뉴" in response.result.text
