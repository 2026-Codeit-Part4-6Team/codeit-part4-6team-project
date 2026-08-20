# TTL 만료 판정 유틸 테스트 — cache/ttl.py와 동일하게 naive datetime 사용
from datetime import datetime, timedelta

from cache.ttl import expired


def test_not_expired_within_ttl() -> None:
    now = datetime(2026, 8, 11, 12, 0, 0)  # noqa: DTZ001
    created_at = now - timedelta(days=3)
    assert expired(created_at, days=7, now=now) is False


def test_expired_past_ttl() -> None:
    now = datetime(2026, 8, 11, 12, 0, 0)  # noqa: DTZ001
    created_at = now - timedelta(days=10)
    assert expired(created_at, days=7, now=now) is True


def test_exact_boundary_is_not_expired() -> None:
    """정확히 TTL만큼 지났다면 아직 만료로 보지 않는다(초과했을 때만 만료)."""
    now = datetime(2026, 8, 11, 12, 0, 0)  # noqa: DTZ001
    created_at = now - timedelta(days=7)
    assert expired(created_at, days=7, now=now) is False
