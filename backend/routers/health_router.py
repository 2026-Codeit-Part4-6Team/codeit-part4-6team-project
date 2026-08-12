from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import inspect
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from backend.database import get_db

REQUIRED_TABLES = {"users", "payments", "generations", "waiting_copies"}

router = APIRouter(tags=["health"])


def is_database_ready(db: Session) -> bool:
    """서비스 DB 연결과 필수 테이블 존재 여부를 확인합니다."""
    try:
        inspector = inspect(db.get_bind())
        return REQUIRED_TABLES.issubset(inspector.get_table_names())
    except SQLAlchemyError:
        return False


@router.get("/health")
def health(db: Annotated[Session, Depends(get_db)]) -> dict[str, str]:
    """서비스 상태를 반환합니다."""
    if not is_database_ready(db):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"status": "unavailable"},
        )
    return {"status": "ok"}
