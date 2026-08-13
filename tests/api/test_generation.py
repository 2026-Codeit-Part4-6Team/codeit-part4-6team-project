from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.auth import get_current_user
from backend.models import Generation, User


class ErrorClient:
    def __init__(self, reason: str):
        self.reason = reason
        self.calls = 0

    async def generate(self, _request):
        self.calls += 1
        return {
            "status": "error",
            "reason": self.reason,
            "message": f"{self.reason} failure",
        }


def add_generation_user(
    db: Session,
    *,
    username="api-generation-user",
    credits=100,
    used=0,
):
    user = User(
        username=username,
        password_hash="unused",
        credits=credits,
        daily_free_used=used,
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


def auth_as(client: TestClient, user: User) -> None:
    client.app.dependency_overrides[get_current_user] = lambda: user


def basic_payload(**overrides):
    payload = {
        "chatbot_type": "basic",
        "question": "신메뉴 광고를 만들어줘",
        "platform": "instagram",
        "max_accepted_credits": 0,
    }
    payload.update(overrides)
    return payload


def test_generate_requires_uuid_idempotency_key(client: TestClient, db_session: Session):
    user = add_generation_user(db_session)
    auth_as(client, user)

    missing = client.post("/generate", json=basic_payload())
    invalid = client.post(
        "/generate",
        headers={"Idempotency-Key": "not-a-uuid"},
        json=basic_payload(),
    )

    assert missing.status_code == 422
    assert invalid.status_code == 422


def test_generate_success_and_same_key_replay_charge_once(
    client: TestClient, db_session: Session
):
    user = add_generation_user(db_session)
    auth_as(client, user)
    key = "00000000-0000-0000-0000-000000000101"

    first = client.post(
        "/generate", headers={"Idempotency-Key": key}, json=basic_payload()
    )
    second = client.post(
        "/generate", headers={"Idempotency-Key": key}, json=basic_payload()
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["generation_id"] == second.json()["generation_id"]
    assert first.json()["status"] == "done"
    db_session.refresh(user)
    assert user.daily_free_used == 1


def test_generate_same_key_different_body_returns_409(
    client: TestClient, db_session: Session
):
    user = add_generation_user(db_session)
    auth_as(client, user)
    key = "00000000-0000-0000-0000-000000000102"
    assert client.post(
        "/generate", headers={"Idempotency-Key": key}, json=basic_payload()
    ).status_code == 200

    conflict = client.post(
        "/generate",
        headers={"Idempotency-Key": key},
        json=basic_payload(question="완전히 다른 요청"),
    )
    assert conflict.status_code == 409


def test_generate_maps_billing_confirmation_and_insufficient_credit(
    client: TestClient, db_session: Session
):
    rich = add_generation_user(
        db_session,
        username="billing-rich",
        credits=100,
        used=10,
    )
    auth_as(client, rich)
    confirmation = client.post(
        "/generate",
        headers={"Idempotency-Key": "00000000-0000-0000-0000-000000000103"},
        json=basic_payload(max_accepted_credits=0),
    )
    assert confirmation.status_code == 409
    assert confirmation.json()["detail"] == {
        "reason": "billing_confirmation_required",
        "required": 50,
        "accepted": 0,
    }

    client.app.dependency_overrides.pop(get_current_user, None)
    poor = add_generation_user(
        db_session,
        username="billing-poor",
        credits=49,
        used=10,
    )
    auth_as(client, poor)
    insufficient = client.post(
        "/generate",
        headers={"Idempotency-Key": "00000000-0000-0000-0000-000000000104"},
        json=basic_payload(max_accepted_credits=50),
    )
    assert insufficient.status_code == 402
    assert insufficient.json()["detail"] == {"required": 50, "current": 49}


def test_generate_maps_missing_source_to_404(client: TestClient, db_session: Session):
    user = add_generation_user(db_session)
    auth_as(client, user)

    response = client.post(
        "/generate",
        headers={"Idempotency-Key": "00000000-0000-0000-0000-000000000105"},
        json=basic_payload(source_gen_id=999999),
    )

    assert response.status_code == 404
    assert db_session.query(Generation).count() == 0


def test_generate_maps_model_error_reasons_to_http_status(
    client: TestClient, db_session: Session
):
    expected = {
        "rate_limit": 429,
        "provider_error": 502,
        "unknown": 500,
    }
    for index, (reason, status_code) in enumerate(expected.items(), start=1):
        user = add_generation_user(
            db_session,
            username=f"error-{reason}",
            used=0,
        )
        auth_as(client, user)
        error_client = ErrorClient(reason)
        client.app.state.chatbot_client = error_client
        response = client.post(
            "/generate",
            headers={
                "Idempotency-Key": f"00000000-0000-0000-0000-00000000020{index}"
            },
            json=basic_payload(),
        )
        assert response.status_code == status_code
        assert error_client.calls == 1
        db_session.refresh(user)
        assert user.daily_free_used == 0
        client.app.dependency_overrides.pop(get_current_user, None)


def test_openapi_generate_uses_generate_request_not_preview(client: TestClient):
    schema = client.app.openapi()
    operation = schema["paths"]["/generate"]["post"]
    request_schema = operation["requestBody"]["content"]["application/json"]["schema"]

    assert request_schema["$ref"].endswith("/GenerateRequest")
    assert "/preview/generate" not in schema["paths"]
