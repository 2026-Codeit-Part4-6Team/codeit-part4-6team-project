import asyncio
from unittest.mock import AsyncMock, Mock

import pytest
from sqlalchemy.exc import IntegrityError

from backend.clients.geocoding_client import GeocodingResult
from backend.schemas import RegisterRequest
from backend.services.auth_service import (
    DuplicateUsernameError,
    GeocodingPolicy,
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
        business_name="카페",
        business_type="카페",
        address="서울",
    )

    with pytest.raises(DuplicateUsernameError):
        asyncio.run(register_user(db, request, geocoder, GeocodingPolicy()))

    assert db.rollback.call_count == 2
