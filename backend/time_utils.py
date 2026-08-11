from datetime import UTC, datetime, time, timedelta
from zoneinfo import ZoneInfo

SEOUL_TIMEZONE = ZoneInfo("Asia/Seoul")


def as_utc(value: datetime) -> datetime:
    """timezone 정보가 없는 DB 시각은 UTC로 간주해 정규화합니다."""
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def next_seoul_midnight_utc(now: datetime) -> datetime:
    """주어진 시각 다음에 오는 한국 자정을 UTC로 반환합니다."""
    current = as_utc(now)
    local_date = current.astimezone(SEOUL_TIMEZONE).date() + timedelta(days=1)
    local_midnight = datetime.combine(local_date, time.min, tzinfo=SEOUL_TIMEZONE)
    return local_midnight.astimezone(UTC)
