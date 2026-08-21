from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.auth import get_current_user
from backend.models import Generation, User


def add_user(db: Session, username="summary-api-owner"):
    user = User(
        username=username,
        password_hash="unused",
        credits=80,
        daily_free_used=9,
        daily_free_reset_at=datetime.now(UTC) - timedelta(minutes=1),
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
            request_hash="b" * 64,
            question="광고",
            platform="banner",
            plan="free",
            status=status,
        )
    )
    db.commit()


def test_user_summary_requires_authentication(client: TestClient):
    assert client.get("/users/me/summary").status_code == 401


def test_user_summary_is_server_calculated_without_mutation(
    client: TestClient, db_session: Session
):
    owner = add_user(db_session)
    other = add_user(db_session, username="summary-api-other")
    add_generation(db_session, owner, 101, status="published")
    add_generation(db_session, owner, 102)
    add_generation(db_session, other, 103, status="published")
    stale_used = owner.daily_free_used
    stale_reset = owner.daily_free_reset_at
    client.app.dependency_overrides[get_current_user] = lambda: owner

    response = client.get("/users/me/summary")

    assert response.status_code == 200
    assert response.json() == {
        "credits": 80,
        "daily_free_remaining": 10,
        "total_generations": 2,
        "published_generations": 1,
    }
    assert owner.daily_free_used == stale_used
    assert owner.daily_free_reset_at == stale_reset
