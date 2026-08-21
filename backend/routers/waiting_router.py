from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.auth import get_current_user
from backend.database import get_db
from backend.models import User, WaitingCopy
from backend.schemas import WaitingCopyResponse

router = APIRouter(tags=["waiting"])


@router.get("/waiting-copies", response_model=WaitingCopyResponse)
def waiting_copy(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> WaitingCopyResponse:
    """업종 문구를 우선하고 없으면 저장된 전체 문구에서 선택합니다."""
    copy = db.scalar(
        select(WaitingCopy)
        .where(WaitingCopy.industry == user.business_type)
        .order_by(func.random())
    )
    if copy is None:
        copy = db.scalar(select(WaitingCopy).order_by(func.random()))
    if copy is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"reason": "waiting_copy_unavailable"},
        )
    return WaitingCopyResponse(
        id=copy.id,
        copy_text=copy.copy_text,
        industry=copy.industry,
    )
