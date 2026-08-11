# cache/ttl.py — 캐시 만료 판정 공통 유틸
from datetime import UTC, datetime, timedelta


def expired(created_at: datetime, days: int, *, now: datetime | None = None) -> bool:
    """created_at으로부터 days일이 지났으면 True. TTL은 데이터별로 호출하는 쪽이 정한다.

    SQLite의 CURRENT_TIMESTAMP(= func.now())는 UTC 기준 naive datetime을 반환한다.
    now 기본값도 반드시 UTC 기준으로 맞춰야 한다 — 로컬 시간(예: KST, UTC+9)을 쓰면
    TTL이 그 시차만큼 일찍 만료된 것으로 계산된다.
    """
    now = now or datetime.now(UTC).replace(tzinfo=None)
    return now - created_at > timedelta(days=days)
