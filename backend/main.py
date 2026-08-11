from fastapi import FastAPI

from backend.routers.generate_router import router as generate_router
from backend.routers.health_router import router as health_router


def create_app() -> FastAPI:
    """FastAPI 애플리케이션을 생성합니다."""
    application = FastAPI(title="Codeit Part 4 Team 6 API")
    application.include_router(health_router)
    application.include_router(generate_router)
    return application


app = create_app()
