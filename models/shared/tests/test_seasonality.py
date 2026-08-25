# models/shared/seasonality.py 테스트 — 두 챗봇 공용 계절성 힌트 계산
from datetime import date

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
        (date(2026, 8, 19), "여름 한창"),  # 여름 말기 경계 직전
        (date(2026, 8, 20), "여름 말기"),  # 경계 당일
        (date(2026, 8, 24), "여름 말기"),  # PM 예시 문항(8월 하순)
        (date(2026, 9, 10), "여름 말기"),  # 경계 구간 마지막 날
        (date(2026, 9, 11), "가을 초입"),  # 경계 직후
    ],
)
def test_season_hint_boundaries(target, expected) -> None:
    assert _season_hint(target) == expected


@pytest.mark.parametrize(
    "target, expected",
    [
        (date(2026, 12, 9), "가을 말기"),  # 겨울 초입 경계 직전 — 12/10부터가 겨울 초입
        (date(2026, 12, 10), "겨울 초입"),
        (date(2027, 1, 5), "겨울 초입"),  # 해가 바뀌어도 같은 구간(연말→연초로 이어짐)
        (date(2027, 1, 9), "겨울 초입"),
        (date(2027, 1, 10), "겨울 한창"),
    ],
)
def test_season_hint_wraps_across_year_boundary(target, expected) -> None:
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


def test_reference_date_uses_kst_today_when_env_var_unset(monkeypatch) -> None:
    monkeypatch.delenv(_ENV_VAR, raising=False)

    # 실행 시각에 좌우되지 않도록, 오늘 날짜가 반환되는지만 확인한다
    # (KST 변환 자체는 별도로 검증하지 않고, 결과가 date 인스턴스인지만 본다).
    result = _reference_date()

    assert isinstance(result, date)


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
