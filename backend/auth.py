from typing import Annotated

import bcrypt
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import User


def hash_password(password: str) -> str:
    """원문 비밀번호를 bcrypt 해시로 변환합니다."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """원문 비밀번호와 bcrypt 해시가 일치하는지 확인합니다."""
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


def get_current_user(
    request: Request, db: Annotated[Session, Depends(get_db)]
) -> User:
    """Session의 user_id로 현재 사용자를 조회합니다."""
    user_id = request.session.get("user_id")
    user = db.get(User, user_id) if isinstance(user_id, int) else None
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "not_authenticated", "message": "로그인이 필요합니다."},
        )
    return user
