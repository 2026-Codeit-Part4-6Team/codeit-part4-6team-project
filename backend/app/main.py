from fastapi import FastAPI

from backend.app.api.router import api_router


def create_app() -> FastAPI:
    """FastAPI 애플리케이션을 생성합니다."""
    application = FastAPI(title="Codeit Part 4 Team 6 API")
    application.include_router(api_router)
    return application


app = create_app()
