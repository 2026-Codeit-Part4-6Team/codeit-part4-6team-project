from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.orm import Session

from backend.database import create_database_engine
from backend.init_db import create_tables
from backend.models import User
from backend.services.credit_service import (
    BillingConfirmationRequired,
    CreditReservation,
    InsufficientCredits,
    apply_generation_usage_rollback,
    credit_cost_for,
    estimate_generation,
    finalize_generation_usage_rollback,
    reserve_generation_usage,
    reset_generation_usage_rollback,
    settle_generation_usage,
)
from backend.services.usage_service import UsageReservation


def make_engine(tmp_path, name="credit.db"):
    engine = create_database_engine(f"sqlite:///{tmp_path / name}")
    create_tables(engine)
    return engine


def add_user(session: Session, *, credits=0, used=0, reset_at=None, username="credit-user"):
    user = User(
        username=username,
        password_hash="hash",
        credits=credits,
        daily_free_used=used,
        daily_free_reset_at=reset_at,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def test_costs_follow_decisions():
    assert credit_cost_for("basic") == 50
    assert credit_cost_for("consultant") == 10
    with pytest.raises(ValueError):
        credit_cost_for("unknown")


def test_estimate_is_virtual_and_does_not_mutate_user(tmp_path):
    engine = make_engine(tmp_path)
    now = datetime(2026, 8, 13, 3, 0, tzinfo=UTC)
    with Session(engine) as db:
        user = add_user(
            db,
            credits=100,
            used=10,
            reset_at=now - timedelta(minutes=1),
        )
        estimate = estimate_generation(user, "basic", now, 10)
        assert estimate.is_free is True
        assert estimate.free_remaining == 10
        assert estimate.estimated_credits == 0
        assert estimate.credits_after == 100
        assert user.daily_free_used == 10
        assert user.credits == 100


def test_paid_estimate_and_insufficient_credit(tmp_path):
    engine = make_engine(tmp_path)
    now = datetime(2026, 8, 13, 3, 0, tzinfo=UTC)
    reset_at = now + timedelta(hours=12)
    with Session(engine) as db:
        rich = add_user(db, credits=50, used=10, reset_at=reset_at, username="rich")
        estimate = estimate_generation(rich, "basic", now, 10)
        assert estimate.is_free is False
        assert estimate.estimated_credits == 50
        assert estimate.credits_after == 0
        assert estimate.requires_confirmation is True

        poor = add_user(db, credits=49, used=10, reset_at=reset_at, username="poor")
        with pytest.raises(InsufficientCredits) as caught:
            estimate_generation(poor, "basic", now, 10)
        assert caught.value.required == 50
        assert caught.value.current == 49
        assert poor.credits == 49


def test_free_is_reserved_before_billing_guard(tmp_path):
    engine = make_engine(tmp_path)
    now = datetime(2026, 8, 13, 3, 0, tzinfo=UTC)
    with Session(engine, expire_on_commit=False) as db:
        user = add_user(db, credits=0, used=0, reset_at=now + timedelta(hours=12))
        reservation = reserve_generation_usage(db, user.id, "basic", now, 10, 0)
        assert isinstance(reservation, UsageReservation)
        db.commit()
        db.refresh(user)
        assert user.daily_free_used == 1
        assert user.credits == 0


def test_billing_guard_never_charges_without_new_consent(tmp_path):
    engine = make_engine(tmp_path)
    now = datetime(2026, 8, 13, 3, 0, tzinfo=UTC)
    with Session(engine, expire_on_commit=False) as db:
        user = add_user(db, credits=100, used=10, reset_at=now + timedelta(hours=12))
        with pytest.raises(BillingConfirmationRequired) as caught:
            reserve_generation_usage(db, user.id, "basic", now, 10, 0)
        assert caught.value.required == 50
        assert caught.value.accepted == 0
        db.rollback()
        db.refresh(user)
        assert user.credits == 100


def test_paid_reservation_charges_actual_cost_only(tmp_path):
    engine = make_engine(tmp_path)
    now = datetime(2026, 8, 13, 3, 0, tzinfo=UTC)
    with Session(engine, expire_on_commit=False) as db:
        user = add_user(db, credits=100, used=10, reset_at=now + timedelta(hours=12))
        reservation = reserve_generation_usage(db, user.id, "basic", now, 10, 999)
        assert isinstance(reservation, CreditReservation)
        assert reservation.credits_used == 50
        db.commit()
        db.refresh(user)
        assert user.credits == 50


def test_credit_compensation_is_atomic_and_retryable(tmp_path):
    engine = make_engine(tmp_path)
    now = datetime(2026, 8, 13, 3, 0, tzinfo=UTC)
    with Session(engine, expire_on_commit=False) as db:
        user = add_user(db, credits=50, used=10, reset_at=now + timedelta(hours=12))
        reservation = reserve_generation_usage(db, user.id, "basic", now, 10, 50)
        db.commit()

        apply_generation_usage_rollback(db, user.id, reservation, now)
        apply_generation_usage_rollback(db, user.id, reservation, now)
        assert reservation.compensation_applied is True
        db.rollback()
        reset_generation_usage_rollback(reservation)
        assert reservation.state == "pending"
        assert reservation.compensation_applied is False

        apply_generation_usage_rollback(db, user.id, reservation, now)
        db.commit()
        finalize_generation_usage_rollback(reservation)
        db.refresh(user)
        assert user.credits == 50
        assert reservation.state == "rolled_back"


def test_settle_prevents_paid_compensation(tmp_path):
    engine = make_engine(tmp_path)
    now = datetime(2026, 8, 13, 3, 0, tzinfo=UTC)
    with Session(engine, expire_on_commit=False) as db:
        user = add_user(db, credits=50, used=10, reset_at=now + timedelta(hours=12))
        reservation = reserve_generation_usage(db, user.id, "basic", now, 10, 50)
        db.commit()
        settle_generation_usage(reservation)
        apply_generation_usage_rollback(db, user.id, reservation, now)
        db.commit()
        db.refresh(user)
        assert reservation.state == "settled"
        assert user.credits == 0


def test_two_concurrent_requests_share_one_remaining_free_slot(tmp_path):
    engine = make_engine(tmp_path, "free-race.db")
    now = datetime(2026, 8, 13, 3, 0, tzinfo=UTC)
    with Session(engine) as db:
        user = add_user(db, credits=100, used=9, reset_at=now + timedelta(hours=12))
        user_id = user.id

    def reserve_once():
        with Session(engine, expire_on_commit=False) as db:
            try:
                reservation = reserve_generation_usage(db, user_id, "basic", now, 10, 0)
                db.commit()
                return reservation.plan
            except BillingConfirmationRequired:
                db.rollback()
                return "confirmation"

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: reserve_once(), range(2)))

    assert sorted(results) == ["confirmation", "free"]
    with Session(engine) as db:
        user = db.get(User, user_id)
        assert user.daily_free_used == 10
        assert user.credits == 100


def test_two_concurrent_paid_requests_never_overdraw(tmp_path):
    engine = make_engine(tmp_path, "credit-race.db")
    now = datetime(2026, 8, 13, 3, 0, tzinfo=UTC)
    with Session(engine) as db:
        user = add_user(db, credits=50, used=10, reset_at=now + timedelta(hours=12))
        user_id = user.id

    def reserve_once():
        with Session(engine, expire_on_commit=False) as db:
            try:
                reserve_generation_usage(db, user_id, "basic", now, 10, 50)
                db.commit()
                return "paid"
            except InsufficientCredits:
                db.rollback()
                return "insufficient"

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: reserve_once(), range(2)))

    assert sorted(results) == ["insufficient", "paid"]
    with Session(engine) as db:
        user = db.get(User, user_id)
        assert user.credits == 0


def test_unknown_chatbot_type_is_rejected_even_when_free_slot_exists(tmp_path):
    engine = make_engine(tmp_path, "unknown.db")
    now = datetime(2026, 8, 13, 3, 0, tzinfo=UTC)
    with Session(engine, expire_on_commit=False) as db:
        user = add_user(db, credits=100, used=0, reset_at=now + timedelta(hours=12))
        with pytest.raises(ValueError):
            estimate_generation(user, "unknown", now, 10)
        with pytest.raises(ValueError):
            reserve_generation_usage(db, user.id, "unknown", now, 10, 0)
        db.rollback()
        db.refresh(user)
        assert user.daily_free_used == 0
        assert user.credits == 100
