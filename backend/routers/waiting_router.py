from random import randrange
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.auth import get_current_user
from backend.database import get_db
from backend.models import User, WaitingCopy
from backend.schemas import WaitingCopyResponse

router = APIRouter(tags=["waiting"])


def _random_waiting_copy(db: Session, industry: str | None = None) -> WaitingCopy | None:
    """기본키 순서에서 임의 offset을 골라 문구를 조회합니다.

    ``ORDER BY random()``은 매 요청마다 전체 행을 정렬합니다. 대기 화면의
    주기적 갱신에서는 count + PK offset으로 정렬 비용과 불필요한 전체 정렬을
    피합니다. 문구가 비어 있으면 호출자가 전역 풀로 재시도합니다.
    """
    filters = [] if industry is None else [WaitingCopy.industry == industry]
    count = db.scalar(
        select(func.count(WaitingCopy.id)).where(*filters)
    ) or 0
    if count == 0:
        return None
    return db.scalar(
        select(WaitingCopy)
        .where(*filters)
        .order_by(WaitingCopy.id)
        .offset(randrange(count))
        .limit(1)
    )


@router.get("/waiting-copies", response_model=WaitingCopyResponse)
def waiting_copy(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> WaitingCopyResponse:
    """업종 문구를 우선하고 없으면 저장된 전체 문구에서 선택합니다."""
    copy = _random_waiting_copy(db, user.business_type)
    if copy is None:
        copy = _random_waiting_copy(db)
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
