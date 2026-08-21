import base64
import json
from asyncio import run

import pytest
from sqlalchemy import update
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from backend.database import create_database_engine
from backend.init_db import create_tables
from backend.models import Generation, User
from backend.schemas import PublishRequest
from backend.services.generation_service import (
    ApprovedImageInvalid,
    ApprovedImageTooLarge,
    PublishedProposalConflict,
    PublishNotFound,
    PublishPersistenceError,
    PublishProposalInvalid,
    PublishStateConflict,
    PublishTypeConflict,
    canonicalize_approved_image,
    publish_generation,
)

PNG = b"\x89PNG\r\n\x1a\n" + b"payload"
JPEG = b"\xff\xd8\xff" + b"payload"
WEBP = b"RIFF" + (4).to_bytes(4, "little") + b"WEBP" + b"payload"


@pytest.mark.parametrize(
    ("data", "mime"),
    [(PNG, "image/png"), (JPEG, "image/jpeg"), (WEBP, "image/webp")],
)
def test_raw_and_data_uri_images_share_one_canonical_value(data, mime):
    raw = base64.b64encode(data).decode()
    expected = f"data:{mime};base64,{raw}"

    assert canonicalize_approved_image(raw, max_image_bytes=100) == expected
    assert (
        canonicalize_approved_image(
            f"data:{mime};base64,{raw}", max_image_bytes=100
        )
        == expected
    )


@pytest.mark.parametrize(
    "value",
    [
        "not-base64",
        "data:text/plain;base64,SGVsbG8=",
        "data:image/png,not-base64",
        "data:image/jpeg;base64,iVBORw0KGgpheWxvYWQ=",
        base64.b64encode(b"unknown-format").decode(),
    ],
)
def test_image_rejects_invalid_encoding_mime_or_signature(value):
    with pytest.raises(ApprovedImageInvalid):
        canonicalize_approved_image(value, max_image_bytes=100)


def test_image_rejects_decoded_bytes_over_limit():
    with pytest.raises(ApprovedImageTooLarge):
        canonicalize_approved_image(
            base64.b64encode(PNG).decode(), max_image_bytes=len(PNG) - 1
        )


def test_none_image_remains_none():
    assert canonicalize_approved_image(None, max_image_bytes=100) is None


def make_engine(tmp_path):
    engine = create_database_engine(f"sqlite:///{tmp_path / 'publish.db'}")
    create_tables(engine)
    return engine


def add_user(db: Session, username: str = "publish-owner") -> User:
    user = User(
        username=username,
        password_hash="hash",
        credits=100,
        business_name="카페 코드잇",
        business_type="카페",
        address="서울 강남구 테헤란로 123",
        lat=37.5,
        lng=127.0,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def basic_result_payload(*, first_copy="제안 1"):
    return {
        "status": "ok",
        "title": "광고 제안",
        "proposals": [
            {"copy": first_copy, "image_b64": None, "error": None},
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
        result_json=result_json
        if result_json is not None
        else json.dumps(basic_result_payload(), ensure_ascii=False),
    )
    db.add(generation)
    db.commit()
    db.refresh(generation)
    return generation


def test_publish_selected_basic_proposal_atomically(tmp_path):
    engine = make_engine(tmp_path)
    with Session(engine) as db:
        user = add_user(db)
        generation = add_generation(db, user)
        image = base64.b64encode(PNG).decode()

        result = run(
            publish_generation(
                db,
                user,
                generation.id,
                PublishRequest(proposal_index=1, image_b64=image),
                max_image_bytes=100,
            )
        )

        assert result.model_dump() == {
            "generation_id": generation.id,
            "status": "published",
            "hitl_approved": True,
            "proposal_index": 1,
        }
        db.refresh(generation)
        assert generation.copy_content == "제안 2"
        assert generation.image_b64 == (
            f"data:image/png;base64,{base64.b64encode(PNG).decode()}"
        )
        assert generation.hitl_approved is True
        assert generation.selected_proposal_index == 1
        assert generation.status == "published"


def test_publish_hides_generation_owned_by_another_user(tmp_path):
    engine = make_engine(tmp_path)
    with Session(engine) as db:
        owner = add_user(db)
        other = add_user(db, username="other-user")
        generation = add_generation(db, owner)

        with pytest.raises(PublishNotFound):
            run(
                publish_generation(
                    db,
                    other,
                    generation.id,
                    PublishRequest(proposal_index=0),
                    max_image_bytes=100,
                )
            )


def test_publish_rejects_generation_before_done(tmp_path):
    engine = make_engine(tmp_path)
    with Session(engine) as db:
        user = add_user(db)
        generation = add_generation(db, user, status="generating")

        with pytest.raises(PublishStateConflict):
            run(
                publish_generation(
                    db,
                    user,
                    generation.id,
                    PublishRequest(proposal_index=0),
                    max_image_bytes=100,
                )
            )


def test_publish_rejects_consultant_generation(tmp_path):
    engine = make_engine(tmp_path)
    with Session(engine) as db:
        user = add_user(db)
        generation = add_generation(
            db,
            user,
            chatbot_type="consultant",
            result_json=json.dumps(
                {
                    "status": "ok",
                    "title": "상권 전략",
                    "strategy": {
                        "summary": "직장인 타깃",
                        "actions": [{"type": "target", "content": "점심 집중"}],
                    },
                    "reasons": ["오피스 상권"],
                    "sources": ["상권 API"],
                    "tokens_used": 2,
                    "suggested_chips": ["메뉴는?", "가격은?", "홍보는?"],
                },
                ensure_ascii=False,
            ),
        )

        with pytest.raises(PublishTypeConflict):
            run(
                publish_generation(
                    db,
                    user,
                    generation.id,
                    PublishRequest(proposal_index=0),
                    max_image_bytes=100,
                )
            )


@pytest.mark.parametrize("result_json", [None, "{not-json"])
def test_publish_rejects_missing_or_corrupt_basic_result(tmp_path, result_json):
    engine = make_engine(tmp_path)
    with Session(engine) as db:
        user = add_user(db)
        generation = add_generation(db, user)
        generation.result_json = result_json
        db.commit()

        with pytest.raises(PublishProposalInvalid):
            run(
                publish_generation(
                    db,
                    user,
                    generation.id,
                    PublishRequest(proposal_index=0),
                    max_image_bytes=100,
                )
            )


def test_publish_rejects_slot_without_copy(tmp_path):
    engine = make_engine(tmp_path)
    payload = basic_result_payload()
    payload["proposals"][0] = {
        "copy": None,
        "image_b64": None,
        "error": {"field": "copy", "reason": "unknown", "message": "실패"},
    }
    with Session(engine) as db:
        user = add_user(db)
        generation = add_generation(
            db, user, result_json=json.dumps(payload, ensure_ascii=False)
        )

        with pytest.raises(PublishProposalInvalid):
            run(
                publish_generation(
                    db,
                    user,
                    generation.id,
                    PublishRequest(proposal_index=0),
                    max_image_bytes=100,
                )
            )


def test_publish_same_proposal_replay_is_idempotent(tmp_path):
    engine = make_engine(tmp_path)
    with Session(engine) as db:
        user = add_user(db)
        generation = add_generation(db, user)
        request = PublishRequest(proposal_index=2)

        first = run(
            publish_generation(
                db, user, generation.id, request, max_image_bytes=100
            )
        )
        replay = run(
            publish_generation(
                db, user, generation.id, request, max_image_bytes=100
            )
        )

        assert replay == first


def test_publish_different_proposal_replay_conflicts(tmp_path):
    engine = make_engine(tmp_path)
    with Session(engine) as db:
        user = add_user(db)
        generation = add_generation(db, user)
        run(
            publish_generation(
                db,
                user,
                generation.id,
                PublishRequest(proposal_index=0),
                max_image_bytes=100,
            )
        )

        with pytest.raises(PublishedProposalConflict):
            run(
                publish_generation(
                    db,
                    user,
                    generation.id,
                    PublishRequest(proposal_index=1),
                    max_image_bytes=100,
                )
            )


def test_publish_compare_and_set_detects_lost_race(tmp_path):
    engine = make_engine(tmp_path)
    with Session(engine) as db:
        user = add_user(db)
        generation = add_generation(db, user)
        original_execute = db.execute
        injected = False

        def execute_with_competing_publish(statement, *args, **kwargs):
            nonlocal injected
            if statement.is_update and not injected:
                injected = True
                original_execute(
                    update(Generation)
                    .where(Generation.id == generation.id)
                    .values(
                        status="published",
                        hitl_approved=True,
                        selected_proposal_index=2,
                        copy_content="제안 3",
                    )
                )
                db.commit()
            return original_execute(statement, *args, **kwargs)

        db.execute = execute_with_competing_publish

        with pytest.raises(PublishedProposalConflict):
            run(
                publish_generation(
                    db,
                    user,
                    generation.id,
                    PublishRequest(proposal_index=0),
                    max_image_bytes=100,
                )
            )


def test_publish_rolls_back_and_preserves_database_failure(tmp_path):
    engine = make_engine(tmp_path)
    with Session(engine) as db:
        user = add_user(db)
        generation = add_generation(db, user)
        _ = user.id
        generation_id = generation.id
        rollback_called = False

        def fail_execute(_statement, *_args, **_kwargs):
            raise OperationalError("UPDATE generations", {}, Exception("db down"))

        original_rollback = db.rollback

        def record_rollback():
            nonlocal rollback_called
            rollback_called = True
            original_rollback()

        db.execute = fail_execute
        db.rollback = record_rollback

        with pytest.raises(PublishPersistenceError):
            run(
                publish_generation(
                    db,
                    user,
                    generation_id,
                    PublishRequest(proposal_index=0),
                    max_image_bytes=100,
                )
            )

        assert rollback_called is True
