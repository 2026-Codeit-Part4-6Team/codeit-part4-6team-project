import bcrypt


def hash_password(password: str) -> str:
    """원문 비밀번호를 bcrypt 해시로 변환합니다."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """원문 비밀번호와 bcrypt 해시가 일치하는지 확인합니다."""
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
