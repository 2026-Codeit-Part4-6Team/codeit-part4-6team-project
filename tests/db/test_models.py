from datetime import UTC, datetime

import pytest
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.config import settings
from backend.database import create_database_engine
from backend.init_db import create_tables
from backend.models import Generation, Payment, User, WaitingCopy


@pytest.fixture
def db_session(tmp_path):
    """격리된 SQLite 세션을 제공합니다."""
    engine = create_database_engine(f"sqlite:///{tmp_path / 'test.db'}")
    create_tables(engine)
    with Session(engine) as session:
        yield session


def make_user(username: str = "owner") -> User:
    """필수 필드만 채운 사용자를 생성합니다."""
    return User(username=username, password_hash="bcrypt-hash")


def test_user_defaults_and_contract_columns(db_session):
    """사용자 기본값과 계약 컬럼을 저장합니다."""
    user = make_user()
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    assert user.id is not None
    assert user.credits == 0
    assert user.daily_free_used == 0
    assert user.api_token_quota == 0
    assert user.is_admin is False
    assert user.created_at is not None

    columns = {column["name"] for column in inspect(db_session.bind).get_columns("users")}
    assert {
        "name",
        "username",
        "email",
        "password_hash",
        "business_name",
        "business_type",
        "lat",
        "lng",
        "address",
        "address_detail",
        "road_address",
        "credits",
        "daily_free_used",
        "daily_free_reset_at",
        "api_token_quota",
        "is_admin",
        "created_at",
    } <= columns


def test_username_is_unique(db_session):
    """사용자명은 중복 저장할 수 없습니다."""
    db_session.add_all([make_user("same"), make_user("same")])

    with pytest.raises(IntegrityError):
        db_session.commit()


def test_generation_has_idempotency_and_result_fields(db_session):
    """생성 이력은 중복 방지와 결과 저장 필드를 포함합니다."""
    user = make_user()
    db_session.add(user)
    db_session.flush()
    generation = Generation(
        user_id=user.id,
        chatbot_type="basic",
        idempotency_key="00000000-0000-0000-0000-000000000001",
        request_hash="a" * 64,
        question="신메뉴 광고를 만들어줘",
        platform="instagram",
        plan="free",
        result_json='{"status":"ok"}',
    )
    db_session.add(generation)
    db_session.commit()
    db_session.refresh(generation)

    assert generation.status == "pending"
    assert generation.credits_used == 0
    assert generation.tokens_used == 0
    assert generation.hitl_approved is False
    assert generation.selected_proposal_index is None


def test_user_idempotency_key_pair_is_unique(db_session):
    """같은 사용자의 Idempotency-Key는 한 번만 저장됩니다."""
    user = make_user()
    db_session.add(user)
    db_session.flush()
    common = {
        "user_id": user.id,
        "chatbot_type": "basic",
        "idempotency_key": "00000000-0000-0000-0000-000000000001",
        "request_hash": "a" * 64,
        "question": "광고를 만들어줘",
        "platform": "banner",
        "plan": "free",
    }
    db_session.add_all([Generation(**common), Generation(**common)])

    with pytest.raises(IntegrityError):
        db_session.commit()


def test_payment_and_waiting_copy_defaults(db_session):
    """결제와 대기 문구의 필수값 및 기본값을 저장합니다."""
    user = make_user()
    db_session.add(user)
    db_session.flush()
    payment = Payment(user_id=user.id, package="starter", amount=1_000, credits=100)
    waiting_copy = WaitingCopy(copy_text="광고 문구를 만들고 있어요.")
    db_session.add_all([payment, waiting_copy])
    db_session.commit()
    db_session.refresh(payment)

    assert payment.method == "mock"
    assert payment.status == "pending"
    assert waiting_copy.created_at is not None


def test_runtime_policy_defaults():
    """초기 Sprint 정책값은 계약과 일치합니다."""
    assert settings.daily_free_limit == 10
    assert settings.basic_credit_cost == 10
    assert settings.consultant_credit_cost == 50
    assert settings.model_request_timeout_seconds == 60


def test_datetime_columns_accept_utc_values(db_session):
    """무료 사용량 리셋 기준을 UTC 시각으로 저장할 수 있습니다."""
    reset_at = datetime(2026, 8, 12, tzinfo=UTC)
    user = make_user()
    user.daily_free_reset_at = reset_at
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    assert user.daily_free_reset_at.replace(tzinfo=UTC) == reset_at
