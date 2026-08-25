# models/shared/seasonality.py 테스트 — 두 챗봇 공용 계절성 힌트 계산
from datetime import UTC, date, datetime
from unittest.mock import patch

import pytest

from models.shared.seasonality import (
    _calendar_period,
    _reference_date,
    _season_hint,
    compute_seasonality,
)

_ENV_VAR = "VALIDATION_REFERENCE_DATE"


@pytest.mark.parametrize(
    "target, expected",
    [
        # 12개 경계 전부를 "경계 전날"·"경계 당일" 쌍으로 검증한다 — 8월(PM 예시)·
        # 12월(연말 wrap-around)만 확인하면 나머지 10개 경계가 잘못 수정돼도
        # 못 잡는다(Codex 리뷰).
        (date(2027, 1, 9), "겨울 초입"),  # 겨울 한창 경계 전날(해 바뀜, 연말 구간 이어짐)
        (date(2027, 1, 10), "겨울 한창"),
        (date(2026, 2, 8), "겨울 한창"),  # 겨울 말기 경계 전날
        (date(2026, 2, 9), "겨울 말기"),
        (date(2026, 3, 20), "겨울 말기"),  # 봄 초입 경계 전날
        (date(2026, 3, 21), "봄 초입"),
        (date(2026, 4, 9), "봄 초입"),  # 봄 한창 경계 전날
        (date(2026, 4, 10), "봄 한창"),
        (date(2026, 4, 29), "봄 한창"),  # 봄 말기 경계 전날
        (date(2026, 4, 30), "봄 말기"),
        (date(2026, 5, 19), "봄 말기"),  # 여름 초입 경계 전날
        (date(2026, 5, 20), "여름 초입"),
        (date(2026, 6, 20), "여름 초입"),  # 여름 한창 경계 전날
        (date(2026, 6, 21), "여름 한창"),
        (date(2026, 8, 19), "여름 한창"),  # 여름 말기 경계 전날
        (date(2026, 8, 20), "여름 말기"),
        (date(2026, 8, 24), "여름 말기"),  # PM 예시 문항(8월 하순)
        (date(2026, 9, 10), "여름 말기"),  # 여름 말기 구간 마지막 날
        (date(2026, 9, 11), "가을 초입"),  # 가을 초입 경계 당일
        (date(2026, 10, 7), "가을 초입"),  # 가을 한창 경계 전날
        (date(2026, 10, 8), "가을 한창"),
        (date(2026, 11, 6), "가을 한창"),  # 가을 말기 경계 전날
        (date(2026, 11, 7), "가을 말기"),
        (date(2026, 12, 9), "가을 말기"),  # 겨울 초입 경계 전날
        (date(2026, 12, 10), "겨울 초입"),  # 연말→연초로 이어짐(다음 항목과 같은 구간)
        (date(2027, 1, 5), "겨울 초입"),  # 해가 바뀌어도 같은 구간
    ],
)
def test_season_hint_boundaries(target, expected) -> None:
    assert _season_hint(target) == expected


@pytest.mark.parametrize(
    "target, expected",
    [
        (date(2026, 8, 1), "8월 상순"),
        (date(2026, 8, 10), "8월 상순"),
        (date(2026, 8, 11), "8월 중순"),
        (date(2026, 8, 20), "8월 중순"),
        (date(2026, 8, 21), "8월 하순"),
        (date(2026, 8, 24), "8월 하순"),
        (date(2026, 2, 28), "2월 하순"),
    ],
)
def test_calendar_period(target, expected) -> None:
    assert _calendar_period(target) == expected


def test_reference_date_uses_env_var_when_set(monkeypatch) -> None:
    monkeypatch.setenv(_ENV_VAR, "2026-07-15")

    assert _reference_date() == date(2026, 7, 15)


@patch("models.shared.seasonality.datetime")
def test_reference_date_uses_kst_today_when_env_var_unset(mock_datetime_cls, monkeypatch) -> None:
    """isinstance(result, date)만 확인하면, 구현이 KST 대신 UTC나 naive 로컬 시각으로
    회귀해도 테스트가 통과해버려 이 설계가 막으려던 자정 전후 날짜 불일치를 못 잡는다
    (Codex 리뷰). UTC 기준 20:00(=KST 기준 다음날 05:00)으로 시각을 고정해, 구현이
    실제로 KST로 변환하는지 날짜 자체로 검증한다."""
    monkeypatch.delenv(_ENV_VAR, raising=False)
    fixed_utc_instant = datetime(2026, 8, 24, 20, 0, tzinfo=UTC)
    mock_datetime_cls.now.side_effect = (
        lambda tz=None: fixed_utc_instant.astimezone(tz) if tz else fixed_utc_instant
    )

    result = _reference_date()

    assert result == date(2026, 8, 25)


@pytest.mark.parametrize("invalid_value", ["2026/07/15", "not-a-date", "2026-13-01", ""])
def test_reference_date_raises_on_malformed_env_var(monkeypatch, invalid_value) -> None:
    """잘못된 형식이면 오늘 날짜로 조용히 대체하지 않고 즉시 예외를 던진다 —
    잘못된 기준일로 평가가 조용히 진행되는 걸 막기 위해서다(PM 리뷰)."""
    monkeypatch.setenv(_ENV_VAR, invalid_value)

    with pytest.raises(ValueError):
        _reference_date()


def test_compute_seasonality_reads_env_var_at_call_time(monkeypatch) -> None:
    """환경변수를 모듈 import 시점이 아니라 호출 시점에 읽어야, 평가 스크립트가
    문항 사이에 값을 바꿔가며 재현성을 확보할 수 있다."""
    monkeypatch.setenv(_ENV_VAR, "2026-08-24")

    result = compute_seasonality()

    assert result == {
        "reference_date": "2026-08-24",
        "calendar_period": "8월 하순",
        "season_hint": "여름 말기",
    }

    monkeypatch.setenv(_ENV_VAR, "2026-01-05")

    result2 = compute_seasonality()

    assert result2 == {
        "reference_date": "2026-01-05",
        "calendar_period": "1월 상순",
        "season_hint": "겨울 초입",
    }
