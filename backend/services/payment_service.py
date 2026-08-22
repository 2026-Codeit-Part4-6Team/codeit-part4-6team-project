from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.models import Payment, User
from backend.schemas import (
    DemoPaymentCatalogResponse,
    DemoPaymentPackage,
    DemoPaymentResponse,
)

UNIT_PRICE = 10
DEMO_PACKAGE_CATALOG = {
    "starter": (48_500, 5_000, 3),
    "standard": (93_000, 10_000, 7),
    "pro": (180_000, 20_000, 10),
}


class DemoPaymentConflict(Exception):
    """같은 키가 다른 데모 패키지에 사용되었습니다."""


class DemoPaymentPersistenceError(Exception):
    """데모 결제와 Credit 갱신을 함께 저장하지 못했습니다."""


def build_demo_catalog(*, enabled: bool) -> DemoPaymentCatalogResponse:
    packages = [
        DemoPaymentPackage(id=package, amount=amount, credits=credits, discount_percent=discount)
        for package, (amount, credits, discount) in DEMO_PACKAGE_CATALOG.items()
    ]
    return DemoPaymentCatalogResponse(
        demo_enabled=enabled,
        packages=packages if enabled else [],
    )


def _response(payment: Payment, user: User) -> DemoPaymentResponse:
    _amount, _credits, discount = DEMO_PACKAGE_CATALOG[payment.package]
    return DemoPaymentResponse(
        payment_id=payment.id,
        package=payment.package,
        amount=payment.amount,
        credits=payment.credits,
        discount_percent=discount,
        balance=user.credits,
        status="completed",
        demo=True,
    )


def complete_demo_payment(
    db: Session,
    user: User,
    package: str,
    idempotency_key: str,
) -> DemoPaymentResponse:
    """데모 Payment 기록과 사용자 Credit 증가를 한 번만 commit합니다."""
    normalized_key = str(UUID(idempotency_key))
    existing = (
        db.query(Payment)
        .filter_by(user_id=user.id, idempotency_key=normalized_key)
        .one_or_none()
    )
    if existing is not None:
        if existing.package != package:
            raise DemoPaymentConflict
        return _response(existing, user)

    amount, credits, _discount = DEMO_PACKAGE_CATALOG[package]
    payment = Payment(
        user_id=user.id,
        idempotency_key=normalized_key,
        package=package,
        amount=amount,
        credits=credits,
        method="demo",
        status="completed",
    )
    user.credits += credits
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
            raise DemoPaymentPersistenceError from error
        if replay.package != package:
            raise DemoPaymentConflict from error
        db.refresh(user)
        return _response(replay, user)
    except Exception as error:
        db.rollback()
        raise DemoPaymentPersistenceError from error
    return _response(payment, user)
