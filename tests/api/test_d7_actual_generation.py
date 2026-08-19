from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.auth import get_current_user
from backend.clients.chatbot_client import ActualChatbotClient
from backend.models import Generation, User


def _add_user(db: Session, *, username: str) -> User:
    user = User(
        username=username,
        password_hash="unused",
        credits=100,
        daily_free_used=0,
        daily_free_reset_at=datetime.now(UTC) + timedelta(hours=12),
        business_name="카페 코드잇",
        business_type="카페",
        address="서울 강남구",
        road_address="서울 강남구 테헤란로 123",
        lat=37.5,
        lng=127.0,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _auth_as(client: TestClient, user: User) -> None:
    client.app.dependency_overrides[get_current_user] = lambda: user


def _payload() -> dict:
    return {
        "chatbot_type": "basic",
        "question": "신메뉴 광고를 만들어줘",
        "platform": "instagram",
        "max_accepted_credits": 0,
    }


def _basic_result() -> dict:
    return {
        "status": "ok",
        "title": "신메뉴 광고",
        "proposals": [
            {"copy": "제안 1", "image_b64": None, "error": None},
            {"copy": "제안 2", "image_b64": None, "error": None},
            {"copy": "제안 3", "image_b64": None, "error": None},
        ],
        "sources": ["상권분석"],
        "tokens_used": 15,
        "suggested_chips": [],
    }


def test_generate_traverses_actual_client_with_plain_dict(
    client: TestClient,
    db_session: Session,
):
    user = _add_user(db_session, username="d7-actual-success")
    _auth_as(client, user)
    seen = []

    def basic_run(payload):
        seen.append(payload)
        return _basic_result()

    client.app.state.chatbot_client = ActualChatbotClient(
        basic_run,
        lambda _payload: {"status": "error", "reason": "unknown", "message": "unused"},
    )

    response = client.post(
        "/generate",
        headers={"Idempotency-Key": "00000000-0000-0000-0000-000000000301"},
        json=_payload(),
    )

    assert response.status_code == 200
    assert response.json()["status"] == "done"
    assert len(response.json()["result"]["proposals"]) == 3
    assert seen[0]["chatbot_type"] == "basic"
    assert isinstance(seen[0]["store"], dict)

    generation = db_session.query(Generation).one()
    assert generation.status == "done"
    assert generation.tokens_used == 15


def test_invalid_actual_result_uses_existing_failure_compensation(
    client: TestClient,
    db_session: Session,
):
    user = _add_user(db_session, username="d7-actual-invalid")
    _auth_as(client, user)

    client.app.state.chatbot_client = ActualChatbotClient(
        lambda _payload: {"status": "ok", "title": "broken"},
        lambda _payload: {"status": "error", "reason": "unknown", "message": "unused"},
    )

    response = client.post(
        "/generate",
        headers={"Idempotency-Key": "00000000-0000-0000-0000-000000000302"},
        json=_payload(),
    )

    assert response.status_code == 500
    assert response.json()["detail"] == {"reason": "unknown"}

    db_session.refresh(user)
    assert user.daily_free_used == 0
    generation = db_session.query(Generation).one()
    assert generation.status == "failed"
    assert generation.credits_used == 0
