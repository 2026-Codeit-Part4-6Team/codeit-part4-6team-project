import json
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import event
from sqlalchemy.orm import Session

from backend.database import create_database_engine
from backend.init_db import create_tables
from backend.models import Generation, User
from backend.services.generation_service import GenerationDataInvariantError
from backend.services.history_service import (
    GenerationHistoryNotFound,
    get_generation_detail,
    list_generations,
)


def make_engine(tmp_path):
    engine = create_database_engine(f"sqlite:///{tmp_path / 'history.db'}")
    create_tables(engine)
    return engine


def add_user(db: Session, username="history-owner"):
    user = User(username=username, password_hash="hash")
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def basic_result():
    return {
        "status": "ok",
        "title": "광고 제안",
        "proposals": [
            {"copy": "제안 1", "error": None},
            {"copy": "제안 2", "error": None},
            {"copy": "제안 3", "error": None},
        ],
        "sources": ["상권분석"],
        "tokens_used": 3,
        "suggested_chips": [],
    }


def consultant_result():
    return {
        "status": "ok",
        "title": "상권 전략",
        "strategy": {
            "summary": "직장인 고객 집중",
            "actions": [{"type": "target", "content": "점심 홍보"}],
        },
        "reasons": ["오피스 상권"],
        "sources": ["상권 API"],
        "tokens_used": 5,
        "suggested_chips": ["메뉴는?", "가격은?", "홍보는?"],
    }


def add_generation(
    db: Session,
    user: User,
    suffix: int,
    *,
    chatbot_type="basic",
    status="done",
    result=None,
    created_at=None,
):
    generation = Generation(
        user_id=user.id,
        chatbot_type=chatbot_type,
        idempotency_key=f"00000000-0000-0000-0000-{suffix:012d}",
        request_hash="c" * 64,
        title="저장 제목",
        question="광고를 만들어줘",
        platform="instagram" if chatbot_type == "basic" else None,
        plan="free",
        status=status,
        result_json=None if result is None else json.dumps(result, ensure_ascii=False),
        created_at=created_at or datetime.now(UTC),
    )
    db.add(generation)
    db.commit()
    db.refresh(generation)
    return generation


def test_list_history_is_owner_scoped_and_newest_first(tmp_path):
    engine = make_engine(tmp_path)
    now = datetime(2026, 8, 21, tzinfo=UTC)
    with Session(engine) as db:
        owner = add_user(db)
        other = add_user(db, "history-other")
        older = add_generation(db, owner, 1, created_at=now - timedelta(days=1))
        newer = add_generation(db, owner, 2, created_at=now)
        add_generation(db, other, 3, created_at=now + timedelta(days=1))

        items = list_generations(db, owner)

        assert [item.id for item in items] == [newer.id, older.id]
        assert "request_hash" not in items[0].model_dump()
        assert "idempotency_key" not in items[0].model_dump()


def test_list_history_uses_id_as_newest_first_tiebreaker(tmp_path):
    engine = make_engine(tmp_path)
    same_time = datetime(2026, 8, 21, tzinfo=UTC)
    with Session(engine) as db:
        owner = add_user(db)
        first = add_generation(db, owner, 4, created_at=same_time)
        second = add_generation(db, owner, 5, created_at=same_time)

        items = list_generations(db, owner)

        assert [item.id for item in items] == [second.id, first.id]


def test_list_history_does_not_select_large_or_internal_columns(tmp_path):
    engine = make_engine(tmp_path)
    with Session(engine) as db:
        owner = add_user(db)
        add_generation(db, owner, 6, result=basic_result())
        statements: list[str] = []

        def capture_statement(_conn, _cursor, statement, _parameters, _context, _many):
            statements.append(statement)

        event.listen(engine, "before_cursor_execute", capture_statement)
        try:
            list_generations(db, owner)
        finally:
            event.remove(engine, "before_cursor_execute", capture_statement)

        history_sql = next(sql for sql in statements if "FROM generations" in sql)
        assert "result_json" not in history_sql
        assert "image_b64" not in history_sql
        assert "request_hash" not in history_sql


def test_list_history_returns_empty_list(tmp_path):
    engine = make_engine(tmp_path)
    with Session(engine) as db:
        owner = add_user(db)
        assert list_generations(db, owner) == []


@pytest.mark.parametrize(
    ("chatbot_type", "payload", "expected_title"),
    [
        ("basic", basic_result(), "광고 제안"),
        ("consultant", consultant_result(), "상권 전략"),
    ],
)
def test_detail_restores_public_success_result(
    tmp_path, chatbot_type, payload, expected_title
):
    engine = make_engine(tmp_path)
    with Session(engine) as db:
        owner = add_user(db)
        generation = add_generation(
            db, owner, 10, chatbot_type=chatbot_type, result=payload
        )

        detail = get_generation_detail(db, owner, generation.id)

        assert detail.result is not None
        assert detail.result.title == expected_title


def test_published_detail_exposes_final_fields(tmp_path):
    engine = make_engine(tmp_path)
    with Session(engine) as db:
        owner = add_user(db)
        generation = add_generation(
            db, owner, 20, status="published", result=basic_result()
        )
        generation.copy_content = "최종 문구"
        generation.image_b64 = "data:image/png;base64,iVBORw0KGgpwYXlsb2Fk"
        generation.selected_proposal_index = 1
        generation.hitl_approved = True
        db.commit()

        detail = get_generation_detail(db, owner, generation.id)

        assert detail.copy_content == "최종 문구"
        assert detail.image_b64 == "data:image/png;base64,iVBORw0KGgpwYXlsb2Fk"
        assert detail.selected_proposal_index == 1
        assert detail.hitl_approved is True


def test_failed_history_exposes_blocked_but_hides_technical_error(tmp_path):
    engine = make_engine(tmp_path)
    with Session(engine) as db:
        owner = add_user(db)
        blocked = add_generation(
            db,
            owner,
            30,
            status="failed",
            result={
                "status": "blocked",
                "action": "reask",
                "reason": "insufficient_info",
                "message": "질문을 보완해 주세요.",
            },
        )
        error = add_generation(
            db,
            owner,
            31,
            status="failed",
            result={
                "status": "error",
                "reason": "provider_error",
                "message": "provider stack detail",
            },
        )

        blocked_detail = get_generation_detail(db, owner, blocked.id)
        error_detail = get_generation_detail(db, owner, error.id)

        assert blocked_detail.result is not None
        assert blocked_detail.result.status == "blocked"
        assert error_detail.result is None
        assert "provider stack detail" not in error_detail.model_dump_json()


def test_detail_hides_other_owner_and_missing_rows(tmp_path):
    engine = make_engine(tmp_path)
    with Session(engine) as db:
        owner = add_user(db)
        other = add_user(db, "history-other")
        generation = add_generation(db, owner, 40)

        with pytest.raises(GenerationHistoryNotFound):
            get_generation_detail(db, other, generation.id)
        with pytest.raises(GenerationHistoryNotFound):
            get_generation_detail(db, owner, 999_999)


def test_detail_rejects_corrupt_stored_result(tmp_path):
    engine = make_engine(tmp_path)
    with Session(engine) as db:
        owner = add_user(db)
        generation = add_generation(db, owner, 50, result=basic_result())
        generation.result_json = "{not-json"
        db.commit()

        with pytest.raises(GenerationDataInvariantError):
            get_generation_detail(db, owner, generation.id)
