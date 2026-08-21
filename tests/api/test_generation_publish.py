import base64
import json
from types import SimpleNamespace

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.auth import get_current_user
from backend.models import Generation, User
from backend.services.generation_service import PublishPersistenceError

PNG = b"\x89PNG\r\n\x1a\n" + b"payload"


def add_user(db: Session, username="publish-api-user") -> User:
    user = User(
        username=username,
        password_hash="unused",
        credits=100,
        business_name="카페 코드잇",
        business_type="카페",
        address="서울 강남구",
        lat=37.5,
        lng=127.0,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def basic_result_payload():
    return {
        "status": "ok",
        "title": "광고 제안",
        "proposals": [
            {"copy": "제안 1", "image_b64": None, "error": None},
            {"copy": "제안 2", "image_b64": None, "error": None},
            {"copy": "제안 3", "image_b64": None, "error": None},
        ],
        "sources": ["Mock 트렌드"],
        "tokens_used": 3,
        "suggested_chips": [],
    }


def add_generation(
    db: Session,
    user: User,
    *,
    status="done",
    chatbot_type="basic",
    result_json=None,
) -> Generation:
    generation = Generation(
        user_id=user.id,
        chatbot_type=chatbot_type,
        idempotency_key=f"00000000-0000-0000-0000-{user.id:012d}",
        request_hash="a" * 64,
        question="광고를 만들어줘",
        platform="instagram" if chatbot_type == "basic" else None,
        plan="free",
        status=status,
        result_json=(
            json.dumps(basic_result_payload(), ensure_ascii=False)
            if result_json is None
            else result_json
        ),
    )
    db.add(generation)
    db.commit()
    db.refresh(generation)
    return generation


def auth_as(client: TestClient, user: User) -> None:
    client.app.dependency_overrides[get_current_user] = lambda: user


def test_publish_requires_authentication(client: TestClient):
    response = client.post(
        "/generations/1/publish",
        json={"proposal_index": 0, "image_b64": None},
    )

    assert response.status_code == 401


def test_publish_returns_approved_generation_contract(
    client: TestClient, db_session: Session
):
    user = add_user(db_session)
    generation = add_generation(db_session, user)
    auth_as(client, user)

    response = client.post(
        f"/generations/{generation.id}/publish",
        json={"proposal_index": 1, "image_b64": None},
    )

    assert response.status_code == 200
    assert response.json() == {
        "generation_id": generation.id,
        "status": "published",
        "hitl_approved": True,
        "proposal_index": 1,
    }


def test_publish_hides_other_users_generation(
    client: TestClient, db_session: Session
):
    owner = add_user(db_session)
    other = add_user(db_session, username="publish-api-other")
    generation = add_generation(db_session, owner)
    auth_as(client, other)

    response = client.post(
        f"/generations/{generation.id}/publish",
        json={"proposal_index": 0, "image_b64": None},
    )

    assert response.status_code == 404
    assert response.json()["detail"]["reason"] == "generation_not_found"


def test_publish_maps_state_and_type_conflicts_to_409(
    client: TestClient, db_session: Session
):
    user = add_user(db_session)
    generating = add_generation(db_session, user, status="generating")
    generating.idempotency_key = "00000000-0000-0000-0000-000000000888"
    consultant = add_generation(
        db_session,
        user,
        chatbot_type="consultant",
        result_json=json.dumps({"not": "used"}),
    )
    db_session.commit()
    auth_as(client, user)

    state_response = client.post(
        f"/generations/{generating.id}/publish",
        json={"proposal_index": 0, "image_b64": None},
    )
    type_response = client.post(
        f"/generations/{consultant.id}/publish",
        json={"proposal_index": 0, "image_b64": None},
    )

    assert state_response.status_code == 409
    assert state_response.json()["detail"]["reason"] == "publish_state_conflict"
    assert type_response.status_code == 409
    assert type_response.json()["detail"]["reason"] == "publish_type_conflict"


def test_publish_maps_invalid_result_and_image_to_422(
    client: TestClient, db_session: Session
):
    user = add_user(db_session)
    invalid_result = add_generation(db_session, user, result_json="{not-json")
    invalid_result.idempotency_key = "00000000-0000-0000-0000-000000000889"
    valid = add_generation(db_session, user)
    db_session.commit()
    auth_as(client, user)

    result_response = client.post(
        f"/generations/{invalid_result.id}/publish",
        json={"proposal_index": 0, "image_b64": None},
    )
    image_response = client.post(
        f"/generations/{valid.id}/publish",
        json={"proposal_index": 0, "image_b64": "not-base64"},
    )

    assert result_response.status_code == 422
    assert result_response.json()["detail"]["reason"] == "invalid_proposal"
    assert image_response.status_code == 422
    assert image_response.json()["detail"]["reason"] == "invalid_approved_image"


def test_publish_maps_decoded_image_limit_to_413(
    client: TestClient, db_session: Session, monkeypatch
):
    from backend.routers import generations_router

    user = add_user(db_session)
    generation = add_generation(db_session, user)
    auth_as(client, user)
    monkeypatch.setattr(
        generations_router,
        "settings",
        SimpleNamespace(max_approved_image_bytes=len(PNG) - 1),
    )

    response = client.post(
        f"/generations/{generation.id}/publish",
        json={
            "proposal_index": 0,
            "image_b64": base64.b64encode(PNG).decode(),
        },
    )

    assert response.status_code == 413
    assert response.json()["detail"]["reason"] == "approved_image_too_large"


def test_publish_different_approved_slot_returns_409(
    client: TestClient, db_session: Session
):
    user = add_user(db_session)
    generation = add_generation(db_session, user)
    auth_as(client, user)
    assert client.post(
        f"/generations/{generation.id}/publish",
        json={"proposal_index": 0, "image_b64": None},
    ).status_code == 200

    response = client.post(
        f"/generations/{generation.id}/publish",
        json={"proposal_index": 2, "image_b64": None},
    )

    assert response.status_code == 409
    assert response.json()["detail"]["reason"] == "published_proposal_conflict"


def test_publish_maps_persistence_failure_to_sanitized_500(
    client: TestClient, db_session: Session, monkeypatch
):
    from backend.routers import generations_router

    user = add_user(db_session)
    generation = add_generation(db_session, user)
    auth_as(client, user)

    async def fail_publish(*_args, **_kwargs):
        raise PublishPersistenceError("database secret")

    monkeypatch.setattr(generations_router, "publish_generation", fail_publish)

    response = client.post(
        f"/generations/{generation.id}/publish",
        json={"proposal_index": 0, "image_b64": None},
    )

    assert response.status_code == 500
    assert response.json()["detail"] == {"reason": "publish_persistence_error"}
    assert "database secret" not in response.text
