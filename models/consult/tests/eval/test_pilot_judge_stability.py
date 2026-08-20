# 컨설턴트 Judge 안정성 파일럿의 생성·반복 채점·리포트 저장을 검증하는 테스트
import json

import pytest

from models.consult.eval import pilot_judge_stability as pilot


def _item(item_id: str = "C-001") -> dict:
    return {
        "id": item_id,
        "area": "consult",
        "question": "주변 경쟁사는 얼마나 되나요?",
        "input": {
            "market_fixture": {
                "fixture_version": "v2-industry-code",
                "captured_at": "2026-08-18",
                "total_count": 100,
                "same_industry_count": 12,
                "nearest_distance_m": 50,
            },
            "trend_fixture": None,
        },
        "expected": {
            "rubric": {
                "근거_충실도": "상권 근거를 정확히 활용한다.",
                "자연스러움": "한국어 문장이 자연스럽다.",
            }
        },
    }


def test_run_pilot_generates_once_and_judges_same_response_three_times(
    monkeypatch,
) -> None:
    item = _item()
    response = {"status": "ok", "strategy": {"summary": "전략"}}
    context = {"market": {"same_industry_count": 12}}
    generated = []
    judged = []

    monkeypatch.setattr(pilot, "preflight", lambda: None)
    monkeypatch.setattr(pilot, "token_snapshot", lambda: {"generation": 0, "judge": 0})
    monkeypatch.setattr(
        pilot,
        "item_token_delta",
        lambda _snapshot: {"generation": 100, "judge": 60},
    )
    monkeypatch.setattr(
        pilot,
        "build_token_usage",
        lambda: {
            "by_model": {"generation-model": 100, "judge-model": 60},
            "generation_tokens": 100,
            "judge_tokens": 60,
            "total_tokens": 160,
            "unattributed_tokens": 0,
        },
    )

    def generate(actual_item: dict) -> tuple[dict, dict]:
        generated.append(actual_item["id"])
        return response, context

    def judge(actual_item: dict, actual_response: dict, actual_context: dict) -> dict:
        judged.append((actual_item["id"], actual_response, actual_context))
        return {"근거_충실도": 4, "자연스러움": 5}

    report = pilot.run_pilot([item], generate=generate, judge=judge)

    assert generated == ["C-001"]
    assert len(judged) == 3
    assert all(call == ("C-001", response, context) for call in judged)
    assert report["passed"] is True
    assert report["unstable_items"] == []
    assert report["items"][0]["spread"] == {"근거_충실도": 0, "자연스러움": 0}
    assert report["items"][0]["tokens"] == {"generation": 100, "judge": 60}


def test_run_pilot_reports_item_when_any_rubric_score_changes(monkeypatch) -> None:
    monkeypatch.setattr(pilot, "preflight", lambda: None)
    monkeypatch.setattr(pilot, "token_snapshot", dict)
    monkeypatch.setattr(pilot, "item_token_delta", lambda _snapshot: {})
    monkeypatch.setattr(pilot, "build_token_usage", dict)
    scores = iter(
        [
            {"근거_충실도": 4, "자연스러움": 5},
            {"근거_충실도": 3, "자연스러움": 5},
            {"근거_충실도": 4, "자연스러움": 5},
        ]
    )

    report = pilot.run_pilot(
        [_item()],
        generate=lambda _item: ({"status": "ok"}, {}),
        judge=lambda _item, _response, _context: next(scores),
    )

    assert report["passed"] is False
    assert report["unstable_items"] == ["C-001"]
    assert report["items"][0]["spread"] == {"근거_충실도": 1, "자연스러움": 0}


def test_load_pilot_items_requires_five_consult_items(tmp_path) -> None:
    dataset_path = tmp_path / "golden.json"
    dataset_path.write_text(
        json.dumps([_item(f"C-{index:03d}") for index in range(1, 5)], ensure_ascii=False),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="5"):
        pilot._load_pilot_items(dataset_path)


def test_generate_once_injects_fixtures_and_returns_runtime_context(monkeypatch) -> None:
    item = _item()
    runtime_context = {"market": {"same_industry_count": 12}, "trend": None}
    response = {"status": "ok", "strategy": {"summary": "전략"}}

    def run_graph(_request: dict) -> tuple[dict, dict]:
        from models.consult.nodes.market_for_consult import get_market
        from models.consult.nodes.trend_for_consult import get_trend

        assert get_market(0, 0) == {
            "total_count": 100,
            "same_industry_count": 12,
            "nearest_distance_m": 50,
        }
        assert get_trend("카페") is None
        return {"context": runtime_context}, response

    monkeypatch.setattr(pilot, "_run_graph", run_graph)

    actual_response, actual_context = pilot._generate_once(item)

    assert actual_response == response
    assert actual_context == runtime_context


def test_generate_once_rejects_error_response(monkeypatch) -> None:
    monkeypatch.setattr(
        pilot,
        "_run_graph",
        lambda _request: ({}, {"status": "error", "reason": "rate_limit"}),
    )

    with pytest.raises(RuntimeError, match="C-001"):
        pilot._generate_once(_item())


def test_main_writes_stability_report(monkeypatch, tmp_path) -> None:
    report = {
        "passed": True,
        "unstable_items": [],
        "generation_model": "generation-model",
        "judge_model": "judge-model",
        "judge_temperature": 0.0,
        "judge_repeat": 3,
        "item_count": 5,
        "token_usage": {"generation_tokens": 100, "judge_tokens": 60},
        "items": [],
    }
    monkeypatch.setattr(pilot, "_load_pilot_items", lambda _path: [_item()] * 5)
    monkeypatch.setattr(pilot, "run_pilot", lambda _items: report)

    exit_code = pilot.main(dataset_path=tmp_path / "golden.json", report_dir=tmp_path)

    report_paths = list(tmp_path.glob("*_consult_judge_stability.json"))
    assert exit_code == 0
    assert len(report_paths) == 1
    assert json.loads(report_paths[0].read_text(encoding="utf-8")) == report
