from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    """서비스 상태를 반환합니다."""
    return {"status": "ok"}
