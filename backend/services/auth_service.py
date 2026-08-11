from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.auth import hash_password, verify_password
from backend.models import User
from backend.schemas import RegisterRequest


class DuplicateUsernameError(Exception):
    """이미 사용 중인 사용자명 오류."""


class DuplicateEmailError(Exception):
    """이미 사용 중인 이메일 오류."""


def register_user(db: Session, request: RegisterRequest) -> User:
    """중복을 확인하고 사용자를 생성합니다."""
    if db.scalar(select(User.id).where(User.username == request.username)) is not None:
        raise DuplicateUsernameError
    if request.email is not None:
        email = str(request.email).lower()
        if db.scalar(select(User.id).where(User.email == email)) is not None:
            raise DuplicateEmailError
    else:
        email = None

    user = User(
        username=request.username,
        email=email,
        password_hash=hash_password(request.password.get_secret_value()),
        name=request.name,
        business_name=request.business_name,
        business_type=request.business_type,
        address=request.address,
        address_detail=request.address_detail,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, username: str, password: str) -> User | None:
    """사용자명과 비밀번호가 일치하는 사용자를 반환합니다."""
    normalized = username.strip().lower()
    user = db.scalar(select(User).where(User.username == normalized))
    if user is None or not verify_password(password, user.password_hash):
        return None
    return user
