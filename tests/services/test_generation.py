import json
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.orm import Session

from backend.database import create_database_engine
from backend.init_db import create_tables
from backend.models import Generation, User
from backend.schemas import GenerateRequest
from backend.services.generation_service import (
    GenerationDataInvariantError,
    IdempotencyConflict,
    ModelExecutionError,
    SourceGenerationConflict,
    SourceGenerationNotFound,
    build_model_request,
    hash_generate_request,
    replay_existing_generation,
)


def make_engine(tmp_path, name="generation.db"):
    engine = create_database_engine(f"sqlite:///{tmp_path / name}")
    create_tables(engine)
    return engine


def add_user(
    db: Session,
    *,
    username="generation-user",
    credits=100,
    used=0,
    reset_at=None,
    business_name="카페 코드잇",
    business_type="카페",
    address="서울 강남구 테헤란로",
    road_address="서울 강남구 테헤란로 123",
    lat=37.5,
    lng=127.0,
):
    user = User(
        username=username,
        password_hash="hash",
        credits=credits,
        daily_free_used=used,
        daily_free_reset_at=reset_at,
        business_name=business_name,
        business_type=business_type,
        address=address,
        road_address=road_address,
        lat=lat,
        lng=lng,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def basic_request(**overrides) -> GenerateRequest:
    payload = {
        "chatbot_type": "basic",
        "question": "신메뉴 광고를 만들어줘",
        "platform": "instagram",
        "max_accepted_credits": 0,
    }
    payload.update(overrides)
    return GenerateRequest.model_validate(payload)


def consultant_request(**overrides) -> GenerateRequest:
    payload = {
        "chatbot_type": "consultant",
        "question": "상권 전략을 알려줘",
        "platform": None,
        "max_accepted_credits": 10,
    }
    payload.update(overrides)
    return GenerateRequest.model_validate(payload)


def consultant_result_payload():
    return {
        "status": "ok",
        "title": "상권 전략",
        "strategy": {
            "summary": "점심 직장인 타깃",
            "actions": [{"type": "target", "content": "직장인 메시지를 강화합니다."}],
        },
        "reasons": ["오피스 상권"],
        "sources": ["Mock 상권분석"],
        "tokens_used": 7,
        "suggested_chips": ["메뉴는?", "가격은?", "홍보는?"],
    }


def basic_result_payload():
    return {
        "status": "ok",
        "title": "광고 제안",
        "proposals": [
            {"copy": "문구 1", "image_b64": None, "error": None},
            {"copy": "문구 2", "image_b64": None, "error": None},
            {"copy": "문구 3", "image_b64": None, "error": None},
        ],
        "sources": ["Mock 트렌드"],
        "tokens_used": 3,
        "suggested_chips": [],
    }


def add_generation(
    db: Session,
    user: User,
    *,
    key="00000000-0000-0000-0000-000000000001",
    request=None,
    status="done",
    chatbot_type="basic",
    result_json=None,
    plan="free",
    credits_used=0,
    source_gen_id=None,
):
    request = request or (
        basic_request() if chatbot_type == "basic" else consultant_request()
    )
    generation = Generation(
        user_id=user.id,
        source_gen_id=source_gen_id,
        chatbot_type=chatbot_type,
        idempotency_key=key,
        request_hash=hash_generate_request(request),
        question=request.question,
        platform=request.platform,
        plan=plan,
        credits_used=credits_used,
        status=status,
        result_json=result_json,
    )
    db.add(generation)
    db.commit()
    db.refresh(generation)
    return generation


def test_request_hash_is_canonical_and_includes_billing_consent():
    first = basic_request(
        extra={"purpose": "출시", "clarification": None},
        max_accepted_credits=0,
    )
    same = GenerateRequest.model_validate(
        {
            "max_accepted_credits": 0,
            "platform": "instagram",
            "extra": {"clarification": None, "purpose": "출시"},
            "question": "신메뉴 광고를 만들어줘",
            "chatbot_type": "basic",
        }
    )
    changed_consent = first.model_copy(update={"max_accepted_credits": 50})

    assert hash_generate_request(first) == hash_generate_request(same)
    assert len(hash_generate_request(first)) == 64
    assert hash_generate_request(first) != hash_generate_request(changed_consent)


def test_build_model_request_uses_server_store_and_source_context(tmp_path):
    engine = make_engine(tmp_path)
    with Session(engine) as db:
        user = add_user(db)
        source_request = consultant_request()
        source = add_generation(
            db,
            user,
            request=source_request,
            chatbot_type="consultant",
            result_json=json.dumps(consultant_result_payload(), ensure_ascii=False),
        )
        request = basic_request(source_gen_id=source.id)

        model_request = build_model_request(db, user, request)

        assert model_request.store.name == user.business_name
        assert model_request.store.address == user.road_address
        assert model_request.source_context is not None
        assert model_request.source_context.generation_id == source.id
        assert model_request.source_context.strategy.summary == "점심 직장인 타깃"


def test_build_model_request_rejects_invalid_store_before_reservation(tmp_path):
    engine = make_engine(tmp_path)
    with Session(engine) as db:
        user = add_user(db, business_name="   ")

        with pytest.raises(GenerationDataInvariantError):
            build_model_request(db, user, basic_request())


def test_source_generation_enforces_owner_type_and_status(tmp_path):
    engine = make_engine(tmp_path)
    with Session(engine) as db:
        owner = add_user(db, username="owner")
        other = add_user(db, username="other")
        source = add_generation(
            db,
            owner,
            request=consultant_request(),
            chatbot_type="consultant",
            result_json=json.dumps(consultant_result_payload(), ensure_ascii=False),
        )

        with pytest.raises(SourceGenerationNotFound):
            build_model_request(db, other, basic_request(source_gen_id=source.id))

        with pytest.raises(SourceGenerationConflict):
            build_model_request(db, owner, consultant_request(source_gen_id=source.id))

        source.status = "failed"
        db.commit()
        with pytest.raises(SourceGenerationConflict):
            build_model_request(db, owner, basic_request(source_gen_id=source.id))


def test_source_generation_corrupt_result_is_server_invariant_failure(tmp_path):
    engine = make_engine(tmp_path)
    with Session(engine) as db:
        user = add_user(db)
        source = add_generation(
            db,
            user,
            request=consultant_request(),
            chatbot_type="consultant",
            result_json='{"status":"ok","title":"broken"}',
        )

        with pytest.raises(GenerationDataInvariantError):
            build_model_request(db, user, basic_request(source_gen_id=source.id))


def test_replay_done_restores_result_and_usage(tmp_path):
    engine = make_engine(tmp_path)
    with Session(engine) as db:
        user = add_user(db)
        request = basic_request()
        generation = add_generation(
            db,
            user,
            request=request,
            result_json=json.dumps(basic_result_payload(), ensure_ascii=False),
        )

        response = replay_existing_generation(generation, request)

        assert response.generation_id == generation.id
        assert response.status == "done"
        assert response.result is not None
        assert response.result.status == "ok"
        assert response.usage.plan == "free"


def test_replay_rejects_same_key_with_different_body(tmp_path):
    engine = make_engine(tmp_path)
    with Session(engine) as db:
        user = add_user(db)
        generation = add_generation(
            db,
            user,
            request=basic_request(),
            status="generating",
            result_json=None,
        )

        with pytest.raises(IdempotencyConflict):
            replay_existing_generation(
                generation,
                basic_request(question="다른 요청"),
            )


def test_replay_failed_blocked_is_public_but_error_is_http_boundary(tmp_path):
    engine = make_engine(tmp_path)
    with Session(engine) as db:
        user = add_user(db)
        blocked_request = basic_request()
        blocked = add_generation(
            db,
            user,
            request=blocked_request,
            status="failed",
            result_json=json.dumps(
                {
                    "status": "blocked",
                    "action": "reask",
                    "reason": "insufficient_info",
                    "message": "추가 정보를 입력해 주세요.",
                },
                ensure_ascii=False,
            ),
        )
        blocked_response = replay_existing_generation(blocked, blocked_request)
        assert blocked_response.status == "failed"
        assert blocked_response.result is not None
        assert blocked_response.result.status == "blocked"

        error_request = basic_request(question="오류 재현")
        error_generation = add_generation(
            db,
            user,
            key="00000000-0000-0000-0000-000000000002",
            request=error_request,
            status="failed",
            result_json=json.dumps(
                {
                    "status": "error",
                    "reason": "provider_error",
                    "message": "provider failed",
                }
            ),
        )
        with pytest.raises(ModelExecutionError) as caught:
            replay_existing_generation(error_generation, error_request)
        assert caught.value.reason == "provider_error"

class RecordingClient:
    def __init__(self, result, *, db: Session | None = None):
        self.result = result
        self.db = db
        self.calls = 0
        self.in_transaction_during_call = None

    async def generate(self, _request):
        self.calls += 1
        if self.db is not None:
            self.in_transaction_during_call = self.db.in_transaction()
        return self.result


class RaisingClient:
    def __init__(self, error: Exception):
        self.error = error
        self.calls = 0

    async def generate(self, _request):
        self.calls += 1
        raise self.error


def basic_result_with_images():
    payload = basic_result_payload()
    for index, proposal in enumerate(payload["proposals"], start=1):
        proposal["image_b64"] = f"image-{index}"
    return payload


def test_generate_free_basic_commits_done_and_strips_images(tmp_path):
    from asyncio import run

    from backend.services.generation_service import generate

    engine = make_engine(tmp_path)
    now = datetime(2026, 8, 13, 3, 0, tzinfo=UTC)
    with Session(engine, expire_on_commit=False) as db:
        user = add_user(db, credits=100, used=0, reset_at=now + timedelta(hours=12))
        request = basic_request(max_accepted_credits=0)
        client = RecordingClient(basic_result_with_images(), db=db)

        response = run(
            generate(
                db,
                user,
                request,
                "00000000-0000-0000-0000-000000000011",
                client,
                now=now,
                free_limit=10,
                model_timeout_seconds=60,
            )
        )

        assert response.status == "done"
        assert response.usage.plan == "free"
        assert response.usage.credits_used == 0
        assert client.calls == 1
        assert client.in_transaction_during_call is False

        db.refresh(user)
        row = db.get(Generation, response.generation_id)
        assert user.daily_free_used == 1
        assert user.credits == 100
        assert row is not None
        assert row.status == "done"
        assert row.tokens_used == 3
        assert "image_b64" not in row.result_json
        assert row.copy_content is None
        assert row.image_b64 is None
        assert row.selected_proposal_index is None
        assert row.hitl_approved is False


def test_generate_paid_consultant_charges_once(tmp_path):
    from asyncio import run

    from backend.services.generation_service import generate

    engine = make_engine(tmp_path)
    now = datetime(2026, 8, 13, 3, 0, tzinfo=UTC)
    with Session(engine, expire_on_commit=False) as db:
        user = add_user(
            db,
            credits=20,
            used=10,
            reset_at=now + timedelta(hours=12),
        )
        request = consultant_request(max_accepted_credits=10)
        client = RecordingClient(consultant_result_payload())

        response = run(
            generate(
                db,
                user,
                request,
                "00000000-0000-0000-0000-000000000012",
                client,
                now=now,
                free_limit=10,
                model_timeout_seconds=60,
            )
        )

        db.refresh(user)
        assert response.status == "done"
        assert response.usage.plan == "paid"
        assert response.usage.credits_used == 10
        assert user.credits == 10
        assert client.calls == 1


def test_generate_billing_confirmation_failure_does_not_insert_or_charge(tmp_path):
    from asyncio import run

    from backend.services.credit_service import BillingConfirmationRequired
    from backend.services.generation_service import generate

    engine = make_engine(tmp_path)
    now = datetime(2026, 8, 13, 3, 0, tzinfo=UTC)
    with Session(engine, expire_on_commit=False) as db:
        user = add_user(
            db,
            credits=100,
            used=10,
            reset_at=now + timedelta(hours=12),
        )
        client = RecordingClient(basic_result_payload())

        with pytest.raises(BillingConfirmationRequired):
            run(
                generate(
                    db,
                    user,
                    basic_request(max_accepted_credits=0),
                    "00000000-0000-0000-0000-000000000013",
                    client,
                    now=now,
                    free_limit=10,
                    model_timeout_seconds=60,
                )
            )

        db.refresh(user)
        assert user.credits == 100
        assert db.query(Generation).count() == 0
        assert client.calls == 0


def test_generate_insufficient_credits_does_not_insert(tmp_path):
    from asyncio import run

    from backend.services.credit_service import InsufficientCredits
    from backend.services.generation_service import generate

    engine = make_engine(tmp_path)
    now = datetime(2026, 8, 13, 3, 0, tzinfo=UTC)
    with Session(engine, expire_on_commit=False) as db:
        user = add_user(
            db,
            credits=49,
            used=10,
            reset_at=now + timedelta(hours=12),
        )

        with pytest.raises(InsufficientCredits):
            run(
                generate(
                    db,
                    user,
                    basic_request(max_accepted_credits=50),
                    "00000000-0000-0000-0000-000000000014",
                    RecordingClient(basic_result_payload()),
                    now=now,
                    free_limit=10,
                    model_timeout_seconds=60,
                )
            )
        assert db.query(Generation).count() == 0


def test_generate_blocked_result_compensates_committed_free_usage(tmp_path):
    from asyncio import run

    from backend.services.generation_service import generate

    engine = make_engine(tmp_path)
    now = datetime(2026, 8, 13, 3, 0, tzinfo=UTC)
    with Session(engine, expire_on_commit=False) as db:
        user = add_user(db, used=0, reset_at=now + timedelta(hours=12))
        blocked = {
            "status": "blocked",
            "action": "reask",
            "reason": "insufficient_info",
            "message": "추가 정보를 입력해 주세요.",
        }

        response = run(
            generate(
                db,
                user,
                basic_request(),
                "00000000-0000-0000-0000-000000000015",
                RecordingClient(blocked),
                now=now,
                free_limit=10,
                model_timeout_seconds=60,
            )
        )

        db.refresh(user)
        row = db.get(Generation, response.generation_id)
        assert response.status == "failed"
        assert response.result is not None
        assert response.result.status == "blocked"
        assert response.usage.credits_used == 0
        assert user.daily_free_used == 0
        assert row is not None
        assert row.status == "failed"
        assert row.credits_used == 0
        assert json.loads(row.result_json)["status"] == "blocked"


def test_generate_error_result_compensates_paid_credit_and_raises(tmp_path):
    from asyncio import run

    from backend.services.generation_service import ModelExecutionError, generate

    engine = make_engine(tmp_path)
    now = datetime(2026, 8, 13, 3, 0, tzinfo=UTC)
    with Session(engine, expire_on_commit=False) as db:
        user = add_user(
            db,
            credits=50,
            used=10,
            reset_at=now + timedelta(hours=12),
        )
        request = basic_request(max_accepted_credits=50)
        key = "00000000-0000-0000-0000-000000000016"

        with pytest.raises(ModelExecutionError) as caught:
            run(
                generate(
                    db,
                    user,
                    request,
                    key,
                    RecordingClient(
                        {
                            "status": "error",
                            "reason": "provider_error",
                            "message": "provider failed",
                        }
                    ),
                    now=now,
                    free_limit=10,
                    model_timeout_seconds=60,
                )
            )

        db.refresh(user)
        row = db.query(Generation).filter_by(idempotency_key=key).one()
        assert caught.value.reason == "provider_error"
        assert user.credits == 50
        assert row.status == "failed"
        assert row.credits_used == 0
        assert json.loads(row.result_json)["reason"] == "provider_error"


def test_generate_client_exception_is_compensated_as_unknown(tmp_path):
    from asyncio import run

    from backend.services.generation_service import ModelExecutionError, generate

    engine = make_engine(tmp_path)
    now = datetime(2026, 8, 13, 3, 0, tzinfo=UTC)
    with Session(engine, expire_on_commit=False) as db:
        user = add_user(
            db,
            credits=50,
            used=10,
            reset_at=now + timedelta(hours=12),
        )
        with pytest.raises(ModelExecutionError) as caught:
            run(
                generate(
                    db,
                    user,
                    basic_request(max_accepted_credits=50),
                    "00000000-0000-0000-0000-000000000017",
                    RaisingClient(RuntimeError("secret provider detail")),
                    now=now,
                    free_limit=10,
                    model_timeout_seconds=60,
                )
            )

        db.refresh(user)
        assert caught.value.reason == "unknown"
        assert "secret provider detail" not in caught.value.message
        assert user.credits == 50


def test_same_key_done_replay_does_not_call_model_or_charge_again(tmp_path):
    from asyncio import run

    from backend.services.generation_service import generate

    engine = make_engine(tmp_path)
    now = datetime(2026, 8, 13, 3, 0, tzinfo=UTC)
    with Session(engine, expire_on_commit=False) as db:
        user = add_user(db, credits=100, used=0, reset_at=now + timedelta(hours=12))
        request = basic_request()
        key = "00000000-0000-0000-0000-000000000018"
        client = RecordingClient(basic_result_payload())

        first = run(
            generate(
                db,
                user,
                request,
                key,
                client,
                now=now,
                free_limit=10,
                model_timeout_seconds=60,
            )
        )
        second = run(
            generate(
                db,
                user,
                request,
                key,
                client,
                now=now + timedelta(seconds=1),
                free_limit=10,
                model_timeout_seconds=60,
            )
        )

        db.refresh(user)
        assert first.generation_id == second.generation_id
        assert client.calls == 1
        assert user.daily_free_used == 1


def test_same_key_generating_before_stale_threshold_returns_current_without_recall(tmp_path):
    from asyncio import run

    from backend.services.generation_service import generate

    engine = make_engine(tmp_path)
    created_at = datetime(2026, 8, 13, 3, 0, tzinfo=UTC)
    with Session(engine, expire_on_commit=False) as db:
        user = add_user(db, credits=50, used=10, reset_at=created_at + timedelta(hours=12))
        request = basic_request(max_accepted_credits=50)
        row = add_generation(
            db,
            user,
            key="00000000-0000-0000-0000-000000000021",
            request=request,
            status="generating",
            plan="paid",
            credits_used=50,
        )
        row.created_at = created_at.replace(tzinfo=None)
        user.credits = 0
        db.commit()
        client = RecordingClient(basic_result_payload())

        response = run(
            generate(
                db,
                user,
                request,
                row.idempotency_key,
                client,
                now=created_at + timedelta(seconds=119),
                free_limit=10,
                model_timeout_seconds=60,
            )
        )

        db.refresh(user)
        assert response.status == "generating"
        assert client.calls == 0
        assert user.credits == 0


def test_stale_paid_generation_refunds_once_and_becomes_failed(tmp_path):
    from backend.services.generation_service import recover_stale_generating

    engine = make_engine(tmp_path)
    created_at = datetime(2026, 8, 13, 3, 0, tzinfo=UTC)
    with Session(engine, expire_on_commit=False) as db:
        user = add_user(db, credits=0, used=10, reset_at=created_at + timedelta(hours=12))
        request = basic_request(max_accepted_credits=50)
        row = add_generation(
            db,
            user,
            request=request,
            status="generating",
            plan="paid",
            credits_used=50,
        )
        row.created_at = created_at.replace(tzinfo=None)
        db.commit()

        assert recover_stale_generating(
            db,
            row,
            user,
            now=created_at + timedelta(seconds=120),
            model_timeout_seconds=60,
        ) is True
        db.refresh(user)
        db.refresh(row)
        assert user.credits == 50
        assert row.status == "failed"
        assert row.credits_used == 0
        assert json.loads(row.result_json)["message"] == "stale_generation_recovered"

        assert recover_stale_generating(
            db,
            row,
            user,
            now=created_at + timedelta(seconds=180),
            model_timeout_seconds=60,
        ) is False
        db.refresh(user)
        assert user.credits == 50


def test_stale_free_generation_decrements_only_same_usage_period(tmp_path):
    from backend.services.generation_service import recover_stale_generating
    from backend.services.usage_service import next_seoul_midnight_utc

    engine = make_engine(tmp_path)
    created_at = datetime(2026, 8, 13, 3, 0, tzinfo=UTC)
    same_period = next_seoul_midnight_utc(created_at)
    with Session(engine, expire_on_commit=False) as db:
        user = add_user(db, used=1, reset_at=same_period)
        request = basic_request()
        row = add_generation(
            db,
            user,
            request=request,
            status="generating",
            plan="free",
            credits_used=0,
        )
        row.created_at = created_at.replace(tzinfo=None)
        db.commit()

        assert recover_stale_generating(
            db,
            row,
            user,
            now=created_at + timedelta(seconds=120),
            model_timeout_seconds=60,
        ) is True
        db.refresh(user)
        assert user.daily_free_used == 0


def test_stale_free_generation_does_not_touch_new_usage_period(tmp_path):
    from backend.services.generation_service import recover_stale_generating
    from backend.services.usage_service import next_seoul_midnight_utc

    engine = make_engine(tmp_path)
    created_at = datetime(2026, 8, 13, 3, 0, tzinfo=UTC)
    old_period = next_seoul_midnight_utc(created_at)
    new_period = old_period + timedelta(days=1)
    with Session(engine, expire_on_commit=False) as db:
        user = add_user(db, used=3, reset_at=new_period)
        row = add_generation(
            db,
            user,
            request=basic_request(),
            status="generating",
            plan="free",
            credits_used=0,
        )
        row.created_at = created_at.replace(tzinfo=None)
        db.commit()

        assert recover_stale_generating(
            db,
            row,
            user,
            now=created_at + timedelta(seconds=120),
            model_timeout_seconds=60,
        ) is True
        db.refresh(user)
        assert user.daily_free_used == 3
