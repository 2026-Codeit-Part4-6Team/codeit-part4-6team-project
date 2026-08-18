import asyncio
from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock

import pytest
from sqlalchemy.exc import IntegrityError

from backend.clients.geocoding_client import GeocodingResult
from backend.models import User
from backend.schemas import RegisterRequest
from backend.services.auth_service import (
    DuplicateUsernameError,
    GeocodingPolicy,
    authenticate_user,
    build_user_response,
    register_user,
)


def test_register_maps_concurrent_username_constraint_to_duplicate_error():
    """DB UNIQUE race는 사전 조회 결과와 무관하게 중복 username 오류가 됩니다."""
    db = Mock()
    db.scalar.side_effect = [None, None, 7]
    db.commit.side_effect = IntegrityError("duplicate", {}, Exception("unique"))
    geocoder = Mock()
    geocoder.geocode = AsyncMock(return_value=GeocodingResult("도로명 주소", 37.5, 127.0))
    request = RegisterRequest(
        username="owner",
        password="safe-password",
        email="owner@example.com",
        business_name="카페",
        business_type="카페",
        address="서울",
    )

    with pytest.raises(DuplicateUsernameError):
        asyncio.run(
            register_user(
                db,
                request,
                geocoder,
                GeocodingPolicy(),
                now=datetime(2026, 8, 13, 6, 0, tzinfo=UTC),
                daily_free_limit=10,
            )
        )

    assert db.rollback.call_count == 2


def test_authenticate_unknown_user_still_verifies_a_password_hash(monkeypatch):
    """존재하지 않는 계정도 bcrypt 검증을 수행해 계정 존재 여부를 숨깁니다."""
    db = Mock()
    db.scalar.return_value = None
    verify = Mock(return_value=False)
    monkeypatch.setattr("backend.services.auth_service.verify_password", verify)

    assert authenticate_user(db, "unknown", "wrong-password") is None

    verify.assert_called_once()


def test_build_user_response_virtual_reset_is_non_mutating():
    """지난 reset 시각은 응답에서만 새 기간으로 보이며 ORM 값은 바꾸지 않습니다."""
    stale_reset = datetime(2026, 8, 12, 15, 0)  # noqa: DTZ001 - SQLite naive UTC
    now = datetime(2026, 8, 13, 6, 0, tzinfo=UTC)
    user = User(
        id=1,
        username="owner",
        password_hash="$2stub$hash",
        credits=25,
        daily_free_used=7,
        daily_free_reset_at=stale_reset,
    )

    response = build_user_response(user, now=now, daily_free_limit=10)

    assert response.daily_free_used == 0
    assert response.daily_free_remaining == 10
    assert response.daily_free_reset_at == datetime(2026, 8, 13, 15, 0, tzinfo=UTC)
    assert user.daily_free_used == 7
    assert user.daily_free_reset_at == stale_reset


def test_build_user_response_preserves_current_period_and_remaining():
    """현재 기간이면 DB 사용량을 유지하고 서버가 잔여 무료 횟수를 계산합니다."""
    reset_at = datetime(2026, 8, 13, 15, 0, tzinfo=UTC)
    now = datetime(2026, 8, 13, 6, 0, tzinfo=UTC)
    user = User(
        id=1,
        username="owner",
        password_hash="$2stub$hash",
        credits=25,
        daily_free_used=3,
        daily_free_reset_at=reset_at,
    )

    response = build_user_response(user, now=now, daily_free_limit=10)

    assert response.daily_free_used == 3
    assert response.daily_free_remaining == 7
    assert response.daily_free_reset_at == reset_at


def test_register_user_uses_supplied_now_for_next_reset():
    """SQLite 회원가입 reset 시각은 전달한 now 기준 naive UTC로 bind합니다."""
    db = Mock()
    db.scalar.side_effect = [None, None]
    db.get_bind.return_value.dialect.name = "sqlite"
    geocoder = Mock()
    geocoder.geocode = AsyncMock(return_value=GeocodingResult("도로명 주소", 37.5, 127.0))
    request = RegisterRequest(
        username="owner",
        password="safe-password",
        email="owner@example.com",
        business_name="카페",
        business_type="카페",
        address="서울",
    )
    now = datetime(2026, 8, 13, 6, 0, tzinfo=UTC)

    asyncio.run(
        register_user(
            db,
            request,
            geocoder,
            GeocodingPolicy(),
            now=now,
            daily_free_limit=10,
        )
    )

    saved_user = db.add.call_args.args[0]
    expected_reset = datetime(2026, 8, 13, 15, 0)  # noqa: DTZ001 - SQLite naive UTC
    assert saved_user.daily_free_reset_at == expected_reset
