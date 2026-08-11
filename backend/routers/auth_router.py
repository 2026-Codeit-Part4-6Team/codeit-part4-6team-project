from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.schemas import RegisterRequest, UserResponse
from backend.services.auth_service import (
    DuplicateEmailError,
    DuplicateUsernameError,
    register_user,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(
    request: RegisterRequest, db: Annotated[Session, Depends(get_db)]
) -> UserResponse:
    """사용자명과 가게 정보로 회원가입합니다."""
    try:
        return UserResponse.model_validate(register_user(db, request))
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
