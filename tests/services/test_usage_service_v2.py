from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from backend.database import create_database_engine
from backend.init_db import create_tables
from backend.models import User
from backend.services.usage_service import (
    UsageReservation,
    apply_free_usage_rollback,
    effective_daily_usage,
    finalize_free_usage_rollback,
    reset_free_usage_rollback,
    settle_free_usage,
    try_reserve_free_usage,
)


def make_db(tmp_path):
    engine = create_database_engine(f"sqlite:///{tmp_path / 'usage.db'}")
    create_tables(engine)
    return engine


def add_user(session: Session, *, used=0, reset_at=None):
    user = User(
        username="usage-user",
        password_hash="hash",
        daily_free_used=used,
        daily_free_reset_at=reset_at,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def test_effective_usage_virtual_reset_does_not_mutate_orm(tmp_path):
    engine = make_db(tmp_path)
    now = datetime(2026, 8, 13, 3, 0, tzinfo=UTC)
    stale_reset = now - timedelta(hours=1)
    with Session(engine) as db:
        user = add_user(db, used=7, reset_at=stale_reset)
        used, reset_at = effective_daily_usage(user, now)
        assert used == 0
        assert reset_at > now
        assert user.daily_free_used == 7
        assert user.daily_free_reset_at.replace(tzinfo=UTC) == stale_reset


def test_free_reservation_uses_db_update_and_rolls_back_once(tmp_path):
    engine = make_db(tmp_path)
    now = datetime(2026, 8, 13, 3, 0, tzinfo=UTC)
    future_reset = now + timedelta(hours=12)
    with Session(engine, expire_on_commit=False) as db:
        user = add_user(db, used=9, reset_at=future_reset)
        reservation = try_reserve_free_usage(db, user.id, now, 10)
        assert isinstance(reservation, UsageReservation)
        assert reservation.state == "pending"
        db.commit()

        db.refresh(user)
        assert user.daily_free_used == 10

        apply_free_usage_rollback(db, user.id, reservation, now)
        apply_free_usage_rollback(db, user.id, reservation, now)
        assert reservation.compensation_applied is True
        db.commit()
        finalize_free_usage_rollback(reservation)

        db.refresh(user)
        assert user.daily_free_used == 9
        assert reservation.state == "rolled_back"
        assert reservation.compensation_applied is False


def test_free_compensation_marker_can_reset_after_db_rollback(tmp_path):
    engine = make_db(tmp_path)
    now = datetime(2026, 8, 13, 3, 0, tzinfo=UTC)
    future_reset = now + timedelta(hours=12)
    with Session(engine, expire_on_commit=False) as db:
        user = add_user(db, used=9, reset_at=future_reset)
        reservation = try_reserve_free_usage(db, user.id, now, 10)
        db.commit()

        apply_free_usage_rollback(db, user.id, reservation, now)
        assert reservation.compensation_applied is True
        db.rollback()
        reset_free_usage_rollback(reservation)
        assert reservation.state == "pending"
        assert reservation.compensation_applied is False

        apply_free_usage_rollback(db, user.id, reservation, now)
        db.commit()
        finalize_free_usage_rollback(reservation)
        db.refresh(user)
        assert user.daily_free_used == 9


def test_old_period_rollback_never_decrements_new_period(tmp_path):
    engine = make_db(tmp_path)
    now = datetime(2026, 8, 13, 3, 0, tzinfo=UTC)
    old_period = now - timedelta(hours=3)
    current_period = now + timedelta(hours=12)
    with Session(engine, expire_on_commit=False) as db:
        user = add_user(db, used=2, reset_at=current_period)
        reservation = UsageReservation(
            plan="free",
            credits_used=0,
            period_reset_at=old_period,
            incremented=True,
        )
        apply_free_usage_rollback(db, user.id, reservation, now)
        db.commit()
        finalize_free_usage_rollback(reservation)
        db.refresh(user)
        assert user.daily_free_used == 2
        assert reservation.state == "rolled_back"


def test_settle_is_terminal_and_blocks_later_rollback(tmp_path):
    engine = make_db(tmp_path)
    now = datetime(2026, 8, 13, 3, 0, tzinfo=UTC)
    future_reset = now + timedelta(hours=12)
    with Session(engine, expire_on_commit=False) as db:
        user = add_user(db, used=0, reset_at=future_reset)
        reservation = try_reserve_free_usage(db, user.id, now, 10)
        db.commit()
        settle_free_usage(reservation)
        assert reservation.state == "settled"

        apply_free_usage_rollback(db, user.id, reservation, now)
        db.commit()
        db.refresh(user)
        assert user.daily_free_used == 1


def test_limit_zero_does_not_mutate_stale_usage(tmp_path):
    engine = make_db(tmp_path)
    now = datetime(2026, 8, 13, 3, 0, tzinfo=UTC)
    stale_reset = now - timedelta(hours=1)
    with Session(engine, expire_on_commit=False) as db:
        user = add_user(db, used=7, reset_at=stale_reset)
        assert try_reserve_free_usage(db, user.id, now, 0) is None
        db.commit()
        db.refresh(user)
        assert user.daily_free_used == 7
        assert user.daily_free_reset_at.replace(tzinfo=UTC) == stale_reset


def test_reservation_performs_lazy_reset_before_increment(tmp_path):
    engine = make_db(tmp_path)
    now = datetime(2026, 8, 13, 3, 0, tzinfo=UTC)
    with Session(engine, expire_on_commit=False) as db:
        user = add_user(db, used=10, reset_at=now - timedelta(minutes=1))
        reservation = try_reserve_free_usage(db, user.id, now, 10)
        db.commit()
        db.refresh(user)
        assert reservation is not None
        assert user.daily_free_used == 1
        assert user.daily_free_reset_at.replace(tzinfo=UTC) > now
