from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.models import Payment, User
from backend.schemas import PaymentCatalogResponse, PaymentPackage, PaymentResponse

UNIT_PRICE = 10
PAYMENT_CATALOG = {
    "starter": {"credits": 5_000, "discount_percent": 3},
    "standard": {"credits": 10_000, "discount_percent": 7},
    "pro": {"credits": 20_000, "discount_percent": 10},
}


class PaymentConflict(Exception):
    """같은 멱등 키가 다른 패키지에 사용되었습니다."""


class PaymentPersistenceError(Exception):
    """결제 기록과 크레딧 반영을 함께 저장하지 못했습니다."""


def _amount(credits: int, discount_percent: int) -> int:
    return credits * UNIT_PRICE * (100 - discount_percent) // 100


def build_catalog() -> PaymentCatalogResponse:
    return PaymentCatalogResponse(
        currency="KRW",
        vat_included=False,
        unit_price=UNIT_PRICE,
        packages=[
            PaymentPackage(
                id=package,
                credits=values["credits"],
                amount=_amount(values["credits"], values["discount_percent"]),
                discount_percent=values["discount_percent"],
            )
            for package, values in PAYMENT_CATALOG.items()
        ],
    )


def _response(payment: Payment, user: User) -> PaymentResponse:
    values = PAYMENT_CATALOG[payment.package]
    return PaymentResponse(
        payment_id=payment.id,
        package=payment.package,
        credits=payment.credits,
        amount=payment.amount,
        discount_percent=values["discount_percent"],
        vat_included=False,
        balance=user.credits,
        status="completed",
        provider="pending",
    )


def complete_payment(
    db: Session, user: User, package: str, idempotency_key: str
) -> PaymentResponse:
    """결제 완료와 Credit 증가를 한 트랜잭션으로 반영합니다.

    현재 PG 의사결정 전 단계에서는 호출 자체를 결제 완료 어댑터로 취급합니다.
    실제 PG 승인 결과를 받는 경계는 이 서비스 함수 앞단에 연결합니다.
    """
    normalized_key = str(UUID(idempotency_key))
    existing = (
        db.query(Payment)
        .filter_by(user_id=user.id, idempotency_key=normalized_key)
        .one_or_none()
    )
    if existing is not None:
        if existing.package != package:
            raise PaymentConflict
        return _response(existing, user)

    values = PAYMENT_CATALOG[package]
    payment = Payment(
        user_id=user.id,
        idempotency_key=normalized_key,
        package=package,
        amount=_amount(values["credits"], values["discount_percent"]),
        credits=values["credits"],
        method="pending_provider",
        status="completed",
    )
    user.credits += values["credits"]
    db.add(payment)
    try:
        db.commit()
        db.refresh(payment)
    except IntegrityError as error:
        db.rollback()
        replay = (
            db.query(Payment)
            .filter_by(user_id=user.id, idempotency_key=normalized_key)
            .one_or_none()
        )
        if replay is None:
            raise PaymentPersistenceError from error
        if replay.package != package:
            raise PaymentConflict from error
        db.refresh(user)
        return _response(replay, user)
    except Exception as error:
        db.rollback()
        raise PaymentPersistenceError from error
    return _response(payment, user)
