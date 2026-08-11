from typing import Annotated

from fastapi import APIRouter, Depends

from backend.auth import get_current_user
from backend.models import User
from backend.schemas import UserResponse

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserResponse)
def read_me(user: Annotated[User, Depends(get_current_user)]) -> UserResponse:
    """현재 로그인한 사용자 정보를 반환합니다."""
    return UserResponse.model_validate(user)
