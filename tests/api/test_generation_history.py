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
        platform="xbanner",
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
    assert client.get("/generations/history").status_code == 401


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
    assert listing.json()[0]["created_at"].endswith("Z")
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


def test_paginated_history_endpoint_supports_search_and_owner_scope(
    client: TestClient, db_session: Session
):
    owner = add_user(db_session, "history-api-page-owner")
    other = add_user(db_session, "history-api-page-other")
    first = add_generation(db_session, owner, 105, basic_result_json())
    first.title = "여름 신메뉴"
    second = add_generation(db_session, owner, 106, basic_result_json())
    second.title = "겨울 메뉴"
    add_generation(db_session, other, 107, basic_result_json()).title = "여름 타인"
    db_session.commit()
    client.app.dependency_overrides[get_current_user] = lambda: owner

    response = client.get("/generations/history?q=여름&page=1&page_size=10")

    assert response.status_code == 200
    assert response.json()["items"][0]["id"] == first.id
    assert response.json()["total"] == 1
    assert response.json()["page"] == 1
    assert response.json()["page_size"] == 10
    assert response.json()["total_pages"] == 1


def test_paginated_history_endpoint_rejects_invalid_page_parameters(
    client: TestClient, db_session: Session
):
    owner = add_user(db_session, "history-api-invalid-page")
    client.app.dependency_overrides[get_current_user] = lambda: owner

    assert client.get("/generations/history?page=0").status_code == 422
    assert client.get("/generations/history?page_size=51").status_code == 422


def test_paginated_history_endpoint_rejects_overlong_query(
    client: TestClient, db_session: Session
):
    owner = add_user(db_session, "history-api-long-query")
    client.app.dependency_overrides[get_current_user] = lambda: owner

    response = client.get(f"/generations/history?q={'x' * 201}")

    assert response.status_code == 422


def test_history_detail_returns_safe_error_reason_without_provider_message(
    client: TestClient, db_session: Session
):
    owner = add_user(db_session)
    generation = add_generation(
        db_session,
        owner,
        105,
        json.dumps(
            {
                "status": "error",
                "reason": "timeout",
                "message": "provider URL and model secret",
            }
        ),
    )
    generation.status = "failed"
    db_session.commit()
    client.app.dependency_overrides[get_current_user] = lambda: owner

    response = client.get(f"/generations/{generation.id}")

    assert response.status_code == 200
    assert response.json()["result"] == {
        "status": "error",
        "reason": "timeout",
        "message": "생성 시간이 초과되었습니다. 잠시 후 다시 시도해 주세요.",
    }
    assert "provider URL and model secret" not in response.text
