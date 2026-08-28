# models/shared/seasonality.py — 날짜 기반 계절성 힌트 계산(두 챗봇 공용, 순수 함수)
"""날씨 API를 새로 연동하는 대신, 요청 시점의 날짜만으로 계절성 힌트를 계산한다
(v3 섹션C, weather 필드 제거와 짝을 이루는 대체안). 외부 I/O가 전혀 없는 순수
함수라 그래프 노드로 감싸는 쪽(각 챗봇의 seasonality_for_* 노드)이 그대로 호출하며,
ModelRequest·서비스 스키마·DB·골든 데이터셋 문항에는 새 필드를 추가하지 않는다."""

import os
from datetime import date, datetime, timedelta, timezone

_KST = timezone(timedelta(hours=9))
_ENV_REFERENCE_DATE = "VALIDATION_REFERENCE_DATE"

# 계절 힌트 경계값 — 실측 근거가 아니라 팀이 정한 정책값이다(PM 리뷰: 8/20~9/10을
# "여름 말기"로 삼은 예시를 그대로 유지하고, 나머지 구간은 봄/여름/가을/겨울을 각각
# 초입·한창·말기 3단계로 나눠 채웠다). (월, 일) 오름차순으로 정렬돼 있어야 하며,
# 마지막 항목(겨울 초입, 12/10~)은 해가 바뀌어 1월 초까지 그대로 이어진다.
_SEASON_BOUNDARIES: list[tuple[tuple[int, int], str]] = [
    ((1, 10), "겨울 한창"),
    ((2, 9), "겨울 말기"),
    ((3, 21), "봄 초입"),
    ((4, 10), "봄 한창"),
    ((4, 30), "봄 말기"),
    ((5, 20), "여름 초입"),
    ((6, 21), "여름 한창"),
    ((8, 20), "여름 말기"),
    ((9, 11), "가을 초입"),
    ((10, 8), "가을 한창"),
    ((11, 7), "가을 말기"),
    ((12, 10), "겨울 초입"),
]


def _season_hint(target: date) -> str:
    """월일만으로 계절 힌트를 판정한다(연도 무관, 경계값은 위 정책표 기준)."""
    value = target.month * 100 + target.day
    # 가장 이른 경계(1/10)보다 앞선 날짜(1/1~1/9)는 전년도 마지막 구간(겨울 초입)이
    # 그대로 이어지는 것이므로, 기본값을 마지막 항목으로 두고 순회하며 갱신한다.
    label = _SEASON_BOUNDARIES[-1][1]
    for (month, day), season_label in _SEASON_BOUNDARIES:
        if value >= month * 100 + day:
            label = season_label
        else:
            break
    return label


def _calendar_period(target: date) -> str:
    """달력 관례(상순 1~10일·중순 11~20일·하순 21일~말일)를 그대로 계산한다 —
    이 구간은 임의 정책이 아니라 표준 표현이라 별도 협의가 필요 없다."""
    if target.day <= 10:
        stage = "상순"
    elif target.day <= 20:
        stage = "중순"
    else:
        stage = "하순"
    return f"{target.month}월 {stage}"


def _reference_date() -> date:
    """VALIDATION_REFERENCE_DATE가 있으면 그 날짜를, 없으면 KST 기준 오늘을 쓴다.

    환경변수 형식이 YYYY-MM-DD가 아니면 오늘 날짜로 조용히 대체하지 않고 즉시
    ValueError를 던진다 — 잘못된 기준일로 평가가 그대로 진행되는 걸 막기 위해서다.
    """
    raw = os.getenv(_ENV_REFERENCE_DATE)
    if raw is None:
        return datetime.now(_KST).date()
    try:
        return date.fromisoformat(raw)
    except ValueError as exc:
        raise ValueError(
            f"{_ENV_REFERENCE_DATE} 형식이 올바르지 않습니다(YYYY-MM-DD 필요): {raw!r}"
        ) from exc


def compute_seasonality() -> dict:
    """기준일의 계절성 힌트를 계산해 반환한다.

    환경변수는 이 함수가 호출될 때마다 읽는다 — 모듈 import 시점에 한 번만 읽으면
    평가 스크립트가 문항 사이에 기준일을 바꿔가며 재현성을 확보할 수 없다.
    """
    reference_date = _reference_date()
    return {
        "reference_date": reference_date.isoformat(),
        "calendar_period": _calendar_period(reference_date),
        "season_hint": _season_hint(reference_date),
    }
