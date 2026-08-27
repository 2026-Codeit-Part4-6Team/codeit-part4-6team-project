from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.middleware.sessions import SessionMiddleware

from backend.clients.chatbot_client import (
    create_chatbot_client,
    preload_actual_model_weights,
)
from backend.config import settings
from backend.routers.auth_router import router as auth_router
from backend.routers.generate_router import router as generate_router
from backend.routers.generations_router import router as generations_router
from backend.routers.health_router import router as health_router
from backend.routers.payments_router import router as payments_router
from backend.routers.users_router import router as users_router
from backend.routers.waiting_router import router as waiting_router


@asynccontextmanager
async def lifespan(_application: FastAPI):
    """실제 모델 모드에서 HF 가중치를 요청 전에 준비합니다."""
    if settings.chatbot_mode == "actual":
        preload_actual_model_weights()
    try:
        yield
    finally:
        application_state = getattr(_application, "state", None)
        chatbot_client = getattr(application_state, "chatbot_client", None)
        close = getattr(chatbot_client, "close", None)
        if callable(close):
            close()


def create_app() -> FastAPI:
    """FastAPI 애플리케이션을 생성합니다."""
    application = FastAPI(title="Codeit Part 4 Team 6 API", lifespan=lifespan)
    application.state.chatbot_client = create_chatbot_client(settings)

    async def close_chatbot_client() -> None:
        close = getattr(application.state.chatbot_client, "close", None)
        if callable(close):
            close()

    application.router.add_event_handler("shutdown", close_chatbot_client)

    application.add_middleware(
        SessionMiddleware,
        secret_key=settings.session_secret_key,
        session_cookie="session",
        max_age=settings.session_max_age_seconds,
        same_site="lax",
        https_only=settings.session_cookie_secure,
    )
    application.include_router(auth_router)
    application.include_router(users_router)
    application.include_router(health_router)
    application.include_router(generate_router)
    application.include_router(generations_router)
    application.include_router(payments_router)
    application.include_router(waiting_router)

    @application.exception_handler(RequestValidationError)
    async def validation_error_handler(
        _request: Request, error: RequestValidationError
    ) -> JSONResponse:
        """검증 오류에서 원문 비밀번호를 제거합니다."""
        sanitized_errors = []
        for item in error.errors():
            sanitized_errors.append(
                {
                    "loc": list(item.get("loc", ())),
                    "type": item.get("type", "value_error"),
                    "msg": item.get("msg", "입력값이 올바르지 않습니다."),
                }
            )
        return JSONResponse(status_code=422, content={"detail": sanitized_errors})

    return application


app = create_app()
