from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from backend.clients.geocoding_client import (
    GeocodingClient,
    GeocodingNotFound,
    GeocodingProviderError,
    get_geocoding_client,
)
from backend.config import settings
from backend.database import get_db
from backend.schemas import LoginRequest, RegisterRequest, UserResponse
from backend.services.auth_service import (
    DuplicateEmailError,
    DuplicateUsernameError,
    GeocodingPolicy,
    authenticate_user,
    register_user,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def get_geocoding_policy() -> GeocodingPolicy:
    """환경변수에서 회원가입 지오코딩 fallback 정책을 구성합니다."""
    return GeocodingPolicy(
        fallback_enabled=settings.geocode_fallback_enabled,
        fallback_lat=settings.geocode_fallback_lat,
        fallback_lng=settings.geocode_fallback_lng,
    )


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    request: RegisterRequest,
    db: Annotated[Session, Depends(get_db)],
    geocoder: Annotated[GeocodingClient, Depends(get_geocoding_client)],
    policy: Annotated[GeocodingPolicy, Depends(get_geocoding_policy)],
) -> UserResponse:
    """사용자명과 가게 정보로 회원가입합니다."""
    try:
        user = await register_user(db, request, geocoder, policy)
        return UserResponse.model_validate(user)
    except DuplicateUsernameError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "duplicate_username", "message": "이미 사용 중인 사용자명입니다."},
        ) from error
    except DuplicateEmailError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "duplicate_email", "message": "이미 사용 중인 이메일입니다."},
        ) from error
    except GeocodingNotFound as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={"code": "address_not_found", "message": "주소 검색 결과가 없습니다."},
        ) from error
    except GeocodingProviderError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "geocoding_unavailable",
                "message": "현재 주소 확인 서비스를 사용할 수 없습니다.",
            },
        ) from error


@router.post("/login", response_model=UserResponse)
def login(
    payload: LoginRequest,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
) -> UserResponse:
    """자격 증명을 확인하고 Session에 사용자 ID를 저장합니다."""
    user = authenticate_user(db, payload.username, payload.password.get_secret_value())
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "invalid_credentials", "message": "사용자명 또는 비밀번호가 올바르지 않습니다."},
        )
    request.session.clear()
    request.session["user_id"] = user.id
    return UserResponse.model_validate(user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(request: Request) -> Response:
    """현재 Session을 제거합니다."""
    request.session.clear()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
