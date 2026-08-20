"""
models/shared/eval/token_usage.py
— 평가 결과 파일의 헤더·토큰 블록 조립 (관리: 전민재 PM, D-278)

세 영역(basic·consult·refusal) 평가 스크립트가 같은 헤더를 만들도록 한 곳에 둔다.
각자 dict 를 조립하면 필드명이 어긋나 compare_reports.py 가 오판한다(D-262).

★ 왜 generation_tokens / judge_tokens 만으로는 안 되는가
  llm.py 의 _total_tokens 는 **모델명**을 키로 집계한다(D-257). 역할이 아니다.
  그런데 config.py 의 OPENAI_JUDGE_MODEL 기본값은 OPENAI_MODEL 과 같다(D-252).
  → env 를 설정하지 않고 평가를 돌리면 두 이름이 같아져 **역할 분리가 원리적으로 불가능**한데,
    역할별 키만 있는 구조는 그때도 숫자를 만들어낸다. 조용히 틀린 값이 남는다.
  그래서 by_model 을 원본으로 남기고 역할별 값은 거기서 파생시킨다.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from models.shared.config import (
    LLM_JUDGE_TEMPERATURE,
    LLM_TEMPERATURE,
    OPENAI_JUDGE_MODEL,
    OPENAI_MODEL,
)
from models.shared.llm import get_total_tokens, reset_total_tokens

KST = timezone(timedelta(hours=9))

# compare_reports.py 의 _CONDITIONS 와 반드시 같아야 한다(기준 문서 §11.2).
# 하나라도 빠지면 before.get(key) 가 None 이 되어 두 결과가 항상 "비교 가능"으로 오판된다.
CONDITION_FIELDS = (
    "generation_model",
    "judge_model",
    "dataset_version",
    "fixture_version",
    "trend_fixture_version",
)


class EvalPreflightError(RuntimeError):
    """평가를 시작하면 안 되는 상태 — 돌리기 전에 멈춘다."""


def preflight(*, require_judge_split: bool = True) -> None:
    """평가 스크립트 맨 앞에서 호출한다.

    1) 누적 카운터를 비운다.
       _total_tokens 는 프로세스 전역이라(D-267) 이전 실행 잔재가 섞이면
       token_usage 가 그만큼 부풀려진다.
    2) 생성 모델과 Judge 모델이 같으면 중단한다.
       같은 이름이면 by_model 에서 역할을 분리할 수 없다 — 숫자를 만들어내는 것보다
       못 만드는 편이 낫다.
    """
    reset_total_tokens()
    if require_judge_split and OPENAI_JUDGE_MODEL == OPENAI_MODEL:
        raise EvalPreflightError(
            f"generation_model 과 judge_model 이 모두 '{OPENAI_MODEL}' 이다. "
            "OPENAI_JUDGE_MODEL 을 .env 에 설정하라(D-274). "
            "같은 모델이면 토큰 역할 분리가 불가능하고, "
            "생성 모델 A/B(D-051) 시 자[尺]가 함께 바뀐다."
        )


def build_token_usage() -> dict:
    """모델별 원본 집계에서 역할별 값을 파생시킨다.

    unattributed_tokens 는 '생성도 채점도 아닌 호출'의 합이다.
    0 이 아니면 계획에 없던 모델 호출이 섞였다는 뜻이므로 반드시 원인을 찾는다.
    (예: 법률 규제 검증 2단 LLM 판정, self_check (B)안, 남아 있는 디버그 호출)
    """
    by_model = {
        name: get_total_tokens(name)
        for name in dict.fromkeys((OPENAI_MODEL, OPENAI_JUDGE_MODEL))
    }
    total = get_total_tokens()
    # 집계에 있지만 위 두 모델이 아닌 것까지 total 에는 포함된다
    generation = get_total_tokens(OPENAI_MODEL)
    judge = get_total_tokens(OPENAI_JUDGE_MODEL) if OPENAI_JUDGE_MODEL != OPENAI_MODEL else 0
    return {
        "by_model": by_model,                       # ★ 원본 — 이 값이 진실이다
        "generation_tokens": generation,            # 파생
        "judge_tokens": judge,                      # 파생
        "total_tokens": total,
        "unattributed_tokens": total - generation - judge,
    }


def build_report_header(
    *,
    area: str,
    dataset_version: str,
    fixture_version: str,
    trend_fixture_version: str,
    item_count: int,
    changed_note: str = "",
) -> dict:
    """결과 파일 헤더 — 기준 문서 §10.4 DoD ⑤ 필드를 빠짐없이 채운다(D-263)."""
    return {
        "run_at": datetime.now(KST).isoformat(timespec="seconds"),
        "area": area,
        "generation_model": OPENAI_MODEL,
        "judge_model": OPENAI_JUDGE_MODEL,
        "generation_temperature": LLM_TEMPERATURE,
        "judge_temperature": LLM_JUDGE_TEMPERATURE,
        "dataset_version": dataset_version,
        "fixture_version": fixture_version,
        "trend_fixture_version": trend_fixture_version,
        "item_count": item_count,
        "changed": changed_note,          # §11.1 "바꾼 것" 한 줄 (D-261)
        "token_usage": build_token_usage(),
    }


def item_token_delta(before: dict[str, int]) -> dict[str, int]:
    """문항 1건이 쓴 토큰 — 문항 처리 전후로 스냅샷을 떠서 뺀다.

    최상위 합계만 남기면 "어느 문항이 비쌌는지" 알 수 없고,
    R- 문항에서 judge 가 0 인지 확인할 수도 없다(D-277).
    """
    return {
        "generation": get_total_tokens(OPENAI_MODEL) - before.get(OPENAI_MODEL, 0),
        "judge": (
            get_total_tokens(OPENAI_JUDGE_MODEL) - before.get(OPENAI_JUDGE_MODEL, 0)
            if OPENAI_JUDGE_MODEL != OPENAI_MODEL
            else 0
        ),
    }


def token_snapshot() -> dict[str, int]:
    """item_token_delta 에 넘길 직전 상태."""
    return {
        name: get_total_tokens(name)
        for name in dict.fromkeys((OPENAI_MODEL, OPENAI_JUDGE_MODEL))
    }


def assert_no_judge_calls(report: dict) -> None:
    """거부(R-) 영역 전용 — Judge 호출이 0 인지 확인한다(D-277).

    R-001~R-015 는 차단 정확도·과잉 차단률·대안 제시율만 재고, 전부 규칙 기반이다
    (기준 문서 §6 · §10.5). Judge 가 돌았다면 평가 코드가 잘못 배선된 것이다.
    """
    judge = report["token_usage"]["judge_tokens"]
    if judge:
        raise EvalPreflightError(
            f"거부 영역에서 judge_tokens={judge} 가 발생했다. "
            "R- 문항은 LLM 호출 0회여야 한다(§10.5)."
        )
