from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from backend.database import create_database_engine
from backend.init_db import create_tables
from backend.models import Generation, User
from backend.services.account_service import build_user_summary


def make_engine(tmp_path):
    engine = create_database_engine(f"sqlite:///{tmp_path / 'account.db'}")
    create_tables(engine)
    return engine


def add_user(db: Session, username="summary-owner", *, used=0, reset_at=None):
    user = User(
        username=username,
        password_hash="hash",
        credits=125,
        daily_free_used=used,
        daily_free_reset_at=reset_at,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def add_generation(db: Session, user: User, suffix: int, status="done"):
    db.add(
        Generation(
            user_id=user.id,
            chatbot_type="basic",
            idempotency_key=f"00000000-0000-0000-0000-{suffix:012d}",
            request_hash="a" * 64,
            question="광고를 만들어줘",
            platform="instagram",
            plan="free",
            status=status,
        )
    )
    db.commit()


def test_summary_counts_only_owner_generations_and_current_usage(tmp_path):
    now = datetime(2026, 8, 21, 1, tzinfo=UTC)
    engine = make_engine(tmp_path)
    with Session(engine) as db:
        owner = add_user(db, used=3, reset_at=now + timedelta(hours=2))
        other = add_user(db, username="summary-other")
        add_generation(db, owner, 1)
        add_generation(db, owner, 2, status="published")
        add_generation(db, owner, 3, status="failed")
        add_generation(db, other, 4, status="published")

        summary = build_user_summary(db, owner, now=now, daily_free_limit=10)

        assert summary.model_dump() == {
            "credits": 125,
            "daily_free_remaining": 7,
            "total_generations": 3,
            "published_generations": 1,
        }


def test_summary_virtual_reset_does_not_mutate_user(tmp_path):
    now = datetime(2026, 8, 21, 1, tzinfo=UTC)
    engine = make_engine(tmp_path)
    with Session(engine) as db:
        user = add_user(db, used=9, reset_at=now - timedelta(seconds=1))
        stale_used = user.daily_free_used
        stale_reset = user.daily_free_reset_at

        summary = build_user_summary(db, user, now=now, daily_free_limit=10)

        assert summary.daily_free_remaining == 10
        assert summary.total_generations == 0
        assert summary.published_generations == 0
        assert user.daily_free_used == stale_used
        assert user.daily_free_reset_at == stale_reset
