from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from backend.auth import get_current_user
from backend.config import settings
from backend.database import get_db
from backend.models import User
from backend.schemas import PaymentCatalogResponse, PaymentRequest, PaymentResponse
from backend.services.payment_service import (
    PaymentConflict,
    PaymentPersistenceError,
    build_catalog,
    complete_payment,
)

router = APIRouter(prefix="/payments", tags=["payments"])


@router.get("/catalog", response_model=PaymentCatalogResponse)
def catalog() -> PaymentCatalogResponse:
    """확정된 크레딧 가격 카탈로그를 반환합니다(VAT 별도)."""
    if not settings.demo_payment_enabled:
        return PaymentCatalogResponse(
            currency="KRW", vat_included=False, unit_price=10, packages=[]
        )
    return build_catalog()


@router.post("", response_model=PaymentResponse, status_code=status.HTTP_201_CREATED)
def purchase(
    body: PaymentRequest,
    idempotency_key: Annotated[UUID, Header(alias="Idempotency-Key")],
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> PaymentResponse:
    """결제 완료를 서버 잔액에 멱등적으로 반영합니다."""
    if not settings.demo_payment_enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"reason": "demo_payment_disabled"},
        )
    try:
        return complete_payment(db, user, body.package, str(idempotency_key))
    except PaymentConflict as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"reason": "payment_idempotency_conflict"},
        ) from error
    except PaymentPersistenceError as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"reason": "payment_persistence_error"},
        ) from error
