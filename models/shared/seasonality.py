# models/shared/seasonality.py — 임시 스텁
from datetime import datetime, timedelta, timezone

_KST = timezone(timedelta(hours=9))


def compute_seasonality() -> dict:
    date = datetime.now(_KST).date()
    return {
        "reference_date": date.isoformat(),
        "calendar_period": "테스트용 임시값",
        "season_hint": "테스트용 임시값",
    }