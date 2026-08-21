import json

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.auth import get_current_user
from backend.models import Generation, User


def add_user(db: Session, username="history-api-owner"):
    user = User(username=username, password_hash="unused")
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def add_generation(db: Session, user: User, suffix: int, result_json=None):
    generation = Generation(
        user_id=user.id,
        chatbot_type="basic",
        idempotency_key=f"00000000-0000-0000-0000-{suffix:012d}",
        request_hash="d" * 64,
        title="API 광고",
        question="광고",
        platform="banner",
        plan="free",
        status="done",
        result_json=result_json,
    )
    db.add(generation)
    db.commit()
    db.refresh(generation)
    return generation


def basic_result_json():
    return json.dumps(
        {
            "status": "ok",
            "title": "광고 제안",
            "proposals": [
                {"copy": "1", "error": None},
                {"copy": "2", "error": None},
                {"copy": "3", "error": None},
            ],
            "sources": [],
            "tokens_used": 1,
            "suggested_chips": [],
        }
    )


def test_history_routes_require_authentication(client: TestClient):
    assert client.get("/generations").status_code == 401
    assert client.get("/generations/1").status_code == 401


def test_history_list_and_detail_are_owner_scoped(
    client: TestClient, db_session: Session
):
    owner = add_user(db_session)
    other = add_user(db_session, "history-api-other")
    generation = add_generation(db_session, owner, 101, basic_result_json())
    add_generation(db_session, other, 102, basic_result_json())
    client.app.dependency_overrides[get_current_user] = lambda: owner

    listing = client.get("/generations")
    detail = client.get(f"/generations/{generation.id}")

    assert listing.status_code == 200
    assert [item["id"] for item in listing.json()] == [generation.id]
    assert detail.status_code == 200
    assert detail.json()["result"]["title"] == "광고 제안"
    assert "request_hash" not in detail.json()


def test_history_detail_returns_404_for_other_owner(
    client: TestClient, db_session: Session
):
    owner = add_user(db_session)
    other = add_user(db_session, "history-api-other")
    generation = add_generation(db_session, other, 103, basic_result_json())
    client.app.dependency_overrides[get_current_user] = lambda: owner

    assert client.get(f"/generations/{generation.id}").status_code == 404


def test_history_detail_sanitizes_corrupt_storage(
    client: TestClient, db_session: Session
):
    owner = add_user(db_session)
    generation = add_generation(db_session, owner, 104, "{not-json")
    client.app.dependency_overrides[get_current_user] = lambda: owner

    response = client.get(f"/generations/{generation.id}")

    assert response.status_code == 500
    assert response.json()["detail"] == {"reason": "generation_data_invariant"}
    assert "not-json" not in response.text
