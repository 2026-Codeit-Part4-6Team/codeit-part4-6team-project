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
    assert insufficient.json()["detail"] == {
        "code": "insufficient_credits",
        "message": "Credit이 부족합니다.",
        "required": 50,
        "current": 49,
    }


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


def test_generate_maps_source_conflict_to_409(client: TestClient, db_session: Session):
    user = add_generation_user(db_session, username="source-conflict")
    auth_as(client, user)

    response = client.post(
        "/generate",
        headers={"Idempotency-Key": "00000000-0000-0000-0000-000000000106"},
        json={
            "chatbot_type": "consultant",
            "question": "기존 컨설팅을 다시 사용하고 싶어요",
            "platform": None,
            "source_gen_id": 1,
            "max_accepted_credits": 0,
        },
    )

    assert response.status_code == 409
    assert response.json()["detail"] == {"reason": "source_generation_conflict"}


def test_generate_maps_store_context_invariant_to_422(
    client: TestClient, db_session: Session, monkeypatch
):
    """서버가 StoreContext를 구성하지 못하면 정책상 422를 반환합니다."""
    from backend.services.generation_service import StoreContextValidationError

    user = add_generation_user(db_session, username="invalid-store-context")
    auth_as(client, user)

    async def raise_invariant(*_args, **_kwargs):
        raise StoreContextValidationError("store context is invalid")

    monkeypatch.setattr(
        "backend.routers.generate_router.generate_generation",
        raise_invariant,
    )

    response = client.post(
        "/generate",
        headers={"Idempotency-Key": "00000000-0000-0000-0000-000000000208"},
        json=basic_payload(),
    )

    assert response.status_code == 422
    assert response.json()["detail"] == {"reason": "generation_data_invariant"}


def test_generate_keeps_storage_invariant_as_500(
    client: TestClient, db_session: Session, monkeypatch
):
    """DB 저장 불변조건 파손은 클라이언트 입력 오류가 아니므로 500을 유지합니다."""
    from backend.services.generation_service import GenerationDataInvariantError

    user = add_generation_user(db_session, username="broken-storage-invariant")
    auth_as(client, user)

    async def raise_invariant(*_args, **_kwargs):
        raise GenerationDataInvariantError("stored result is corrupt")

    monkeypatch.setattr(
        "backend.routers.generate_router.generate_generation",
        raise_invariant,
    )

    response = client.post(
        "/generate",
        headers={"Idempotency-Key": "00000000-0000-0000-0000-000000000207"},
        json=basic_payload(),
    )

    assert response.status_code == 500
    assert response.json()["detail"] == {"reason": "generation_data_invariant"}


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


def test_generate_maps_model_timeout_to_504(
    client: TestClient, db_session: Session, monkeypatch
):
    """Service timeout은 Public HTTP 504 경계로 변환합니다."""
    from backend.services.generation_service import ModelExecutionError

    user = add_generation_user(db_session, username="error-timeout")
    auth_as(client, user)

    async def raise_timeout(*_args, **_kwargs):
        raise ModelExecutionError(reason="timeout", message="provider timeout")

    monkeypatch.setattr(
        "backend.routers.generate_router.generate_generation",
        raise_timeout,
    )

    response = client.post(
        "/generate",
        headers={"Idempotency-Key": "00000000-0000-0000-0000-000000000209"},
        json=basic_payload(),
    )

    assert response.status_code == 504
    assert response.json()["detail"] == {"reason": "timeout"}
