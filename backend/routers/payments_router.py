from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from backend.auth import get_current_user
from backend.config import settings
from backend.database import get_db
from backend.models import User
from backend.schemas import (
    DemoPaymentCatalogResponse,
    DemoPaymentRequest,
    DemoPaymentResponse,
)
from backend.services.payment_service import (
    DemoPaymentConflict,
    DemoPaymentPersistenceError,
    build_demo_catalog,
    complete_demo_payment,
)

router = APIRouter(prefix="/payments", tags=["payments"])


@router.get("/catalog", response_model=DemoPaymentCatalogResponse)
def catalog() -> DemoPaymentCatalogResponse:
    """데모가 꺼져 있으면 가격 정책을 노출하지 않습니다."""
    return build_demo_catalog(enabled=settings.demo_payment_enabled)


@router.post("", response_model=DemoPaymentResponse, status_code=status.HTTP_201_CREATED)
def purchase(
    body: DemoPaymentRequest,
    idempotency_key: Annotated[UUID, Header(alias="Idempotency-Key")],
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> DemoPaymentResponse:
    """명시적으로 활성화한 데모 환경에서만 Credit을 충전합니다."""
    if not settings.demo_payment_enabled:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    try:
        return complete_demo_payment(db, user, body.package, str(idempotency_key))
    except DemoPaymentConflict as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"reason": "payment_idempotency_conflict"},
        ) from error
    except DemoPaymentPersistenceError as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"reason": "payment_persistence_error"},
        ) from error
