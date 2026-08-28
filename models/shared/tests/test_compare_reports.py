"""
models/shared/tests/test_compare_reports.py
— 비교 가능성 판정 테스트 (D-281)

★ 이 테스트는 "문서 §11.2 초안이 통과시켰던 케이스"를 하나씩 고정한다.
  초안 로직으로 되돌아가면 여기가 빨간불이 된다.
"""

import json

import pytest

from models.shared.eval.compare_reports import (
    compare_reports,
    render_markdown,
    validate_report,
)

BASE = {
    "run_at": "2026-08-21T18:00:00+09:00",
    "area": "basic",
    "generation_model": "gpt-4o-mini",
    "judge_model": "gpt-4.1-mini",
    "generation_temperature": 0.3,
    "judge_temperature": 0.0,
    "dataset_version": "v1.3",
    "fixture_version": "v2-industry-code",
    "trend_fixture_version": "v1-naver-apihub",
    "item_count": 25,
    "changed": "copy_gen.py SYSTEM_PROMPT few-shot 2개 추가",
    "token_usage": {
        "by_model": {"gpt-4o-mini": 12000, "gpt-4.1-mini": 4000},
        "generation_tokens": 12000,
        "judge_tokens": 4000,
        "total_tokens": 16000,
        "unattributed_tokens": 0,
    },
    "metrics": {"llm_judge_avg": 3.2, "contract_compliance": 0.88, "failure_rate": 0.12},
}


@pytest.fixture
def write(tmp_path):
    def _w(name: str, **over) -> str:
        data = json.loads(json.dumps(BASE))
        for key in over.pop("_drop", []):
            data.pop(key, None)
        data.update(over)
        path = tmp_path / f"{name}.json"
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        return str(path)

    return _w


# ── 초안 결함 ① 헤더가 양쪽 다 없으면 "같다"로 판정됐다 ──────────────────────
def test_missing_header_is_not_comparable(write):
    before = write("before", _drop=["judge_model", "fixture_version", "judge_temperature"])
    after = write("after", metrics={"llm_judge_avg": 4.1})
    r = compare_reports(before, after)
    assert r["comparable"] is False
    assert any("judge_model" in p for p in r["problems"])
    assert any("judge_temperature" in p for p in r["problems"])


# ── 초안 결함 ② area 를 보지 않았다 ─────────────────────────────────────────
def test_different_area_is_not_comparable(write):
    r = compare_reports(write("b"), write("a", area="consult"))
    assert r["comparable"] is False
    assert r["changed"] == ["area"]


# ── 초안 결함 ③ item_count 를 보지 않았다 ───────────────────────────────────
def test_item_count_mismatch_is_not_comparable(write):
    r = compare_reports(write("b"), write("a", item_count=24))
    assert r["comparable"] is False
    assert "item_count" in r["changed"]


def test_item_count_may_differ_when_dataset_version_differs(write):
    """dataset_version 이 다르면 어차피 비교 불가라 item_count 를 따로 탓하지 않는다."""
    r = compare_reports(write("b"), write("a", dataset_version="v1.4", item_count=30))
    assert r["comparable"] is False
    assert "dataset_version" in r["changed"]


# ── 초안 결함 ④ judge_temperature 오염을 보지 않았다 ────────────────────────
def test_nonzero_judge_temperature_is_rejected(write):
    r = compare_reports(write("b"), write("a", judge_temperature=0.3))
    assert r["comparable"] is False
    assert any("judge_temperature" in p for p in r["problems"])


# ── 초안 유지분: §11.2.1 표 ────────────────────────────────────────────────
def test_prompt_only_change_is_comparable(write):
    r = compare_reports(write("b"), write("a", metrics={"llm_judge_avg": 4.1}))
    assert r["comparable"] is True
    assert r["means"] == "프롬프트 튜닝 효과"
    assert r["changed"] == []


def test_generation_model_alone_is_comparable(write):
    r = compare_reports(write("b"), write("a", generation_model="gpt-5.4-mini"))
    assert r["comparable"] is True
    assert r["means"] == "생성 모델 성능 차이"


def test_both_models_changed_is_not_comparable(write):
    """§11.2.2 '자[尺]와 대상을 동시에 바꾸면 눈금을 신뢰할 수 없다'."""
    r = compare_reports(
        write("b"), write("a", generation_model="gpt-5.4-mini", judge_model="gpt-5.4")
    )
    assert r["comparable"] is False
    assert set(r["changed"]) == {"generation_model", "judge_model"}


def test_judge_model_alone_carries_caveat(write):
    """비교는 되지만 baseline 으로 쓰면 안 된다는 단서가 붙는다(D-258)."""
    r = compare_reports(write("b"), write("a", judge_model="gpt-5.4"))
    assert r["comparable"] is True
    assert any("baseline" in w for w in r["warnings"])


def test_missing_changed_note_warns(write):
    """§11.1 '바꾼 것' 한 줄이 없으면 경고한다(D-261)."""
    r = compare_reports(write("b"), write("a", changed=""))
    assert r["comparable"] is True
    assert any("바꾼 것" in w for w in r["warnings"])


# ── 단독 검증 모드 — 1차 측정 직후에 쓴다 ──────────────────────────────────
def test_validate_catches_unattributed_tokens():
    report = json.loads(json.dumps(BASE))
    report["token_usage"]["unattributed_tokens"] = 500
    problems = validate_report(report)
    assert any("unattributed_tokens" in p for p in problems)


def test_validate_catches_judge_call_in_refusal_area():
    report = json.loads(json.dumps(BASE))
    report["area"] = "refusal"
    problems = validate_report(report)
    assert any("R-" in p for p in problems)


def test_validate_passes_on_healthy_report():
    assert validate_report(json.loads(json.dumps(BASE))) == []


# ── 발표용 표 ──────────────────────────────────────────────────────────────
def test_markdown_matches_section_11_format(write):
    before = write("b")
    after = write("a", metrics={"llm_judge_avg": 4.1, "contract_compliance": 1.0,
                                "failure_rate": 0.03})
    md = render_markdown(compare_reports(before, after), before, after)
    assert "| 지표 | 튜닝 전 | 튜닝 후 | 변화 |" in md
    assert "88.0% | 100.0% | **+12.0%p**" in md      # 비율은 %p 로 환산
    assert "-9.0%p" in md                             # 낮을수록 좋은 지표도 강조
    assert "측정 조건" in md and "바꾼 것" in md      # D-261
