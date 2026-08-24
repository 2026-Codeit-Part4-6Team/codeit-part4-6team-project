# 컨설턴트 suggested_chips 전용 평가기의 연결·규칙 검사·Judge 흐름을 검증하는 테스트
import json
from datetime import datetime
from unittest.mock import patch
from zoneinfo import ZoneInfo

import httpx
import openai
import pytest

from models.consult.eval.eval_suggested_chips import (
    AREA,
    JUDGE_SYSTEM_PROMPT,
    _build_report,
    _check_chips_contract,
    _evaluate_item,
    _has_exact_duplicate,
    _load_chips_items,
    _load_dataset_index,
    _parse_args,
    _source_provenance,
    evaluate_chips,
)
from models.shared.config import OPENAI_MODEL
from models.shared.eval.token_usage import EvalPreflightError

_STORE = {
    "name": "카페 코드잇", "type": "카페", "address": "서울 강남구 역삼동",
    "lat": 37.4979, "lng": 127.0276,
}


def _dataset(*, item_id: str = "C-001", area: str = "consult") -> list[dict]:
    return [
        {
            "id": item_id,
            "area": area,
            "question": "주변 경쟁사는 얼마나 되나요?",
            "input": {"store": _STORE},
        }
    ]


def _report_item(
    *, item_id: str = "C-001", status: str = "ok", chips: list | None = None
) -> dict:
    chips = chips if chips is not None else ["메뉴는요?", "홍보는요?", "단골은요?"]
    response: dict = {"status": status}
    if status == "ok":
        response.update(
            {
                "strategy": {"summary": "요약", "actions": [{"type": "menu", "content": "행동"}]},
                "suggested_chips": chips,
            }
        )
    return {"id": item_id, "response": response}


def _source_report(*, items: list[dict] | None = None, generation_model: str = OPENAI_MODEL) -> dict:
    return {
        "run_at": "2026-08-22T15:52:11+09:00",
        "generation_model": generation_model,
        "generation_temperature": 0.3,
        "fixture_version": "v2-industry-code",
        "trend_fixture_version": "v1-naver-apihub",
        "items": items if items is not None else [_report_item()],
    }


def test_load_dataset_index_filters_area_and_uses_default_store() -> None:
    dataset = _dataset() + [
        {"id": "B-001", "area": "basic", "question": "무시할 질문", "input": {}}
    ]

    index = _load_dataset_index(dataset)

    assert set(index) == {"C-001"}
    assert index["C-001"] == {"question": "주변 경쟁사는 얼마나 되나요?", "store": _STORE}


def test_load_chips_items_links_by_id_and_extracts_strategy() -> None:
    dataset_index = _load_dataset_index(_dataset())
    report = _source_report()

    items, excluded = _load_chips_items(report, dataset_index)

    assert excluded == []
    assert items == [
        {
            "id": "C-001",
            "question": "주변 경쟁사는 얼마나 되나요?",
            "store": _STORE,
            "chips": ["메뉴는요?", "홍보는요?", "단골은요?"],
            "strategy_summary": "요약",
            "strategy_actions": [{"type": "menu", "content": "행동"}],
        }
    ]


def test_load_chips_items_excludes_missing_dataset_id() -> None:
    dataset_index = _load_dataset_index(_dataset(item_id="C-999"))
    report = _source_report()

    items, excluded = _load_chips_items(report, dataset_index)

    assert items == []
    assert excluded == [{"id": "C-001", "reason": "dataset_id_not_found"}]


def test_load_chips_items_excludes_non_ok_status() -> None:
    dataset_index = _load_dataset_index(_dataset())
    report = _source_report(items=[_report_item(status="error")])

    items, excluded = _load_chips_items(report, dataset_index)

    assert items == []
    assert excluded == [{"id": "C-001", "reason": "source_response_not_ok"}]


def test_check_chips_contract_true_for_three_nonempty_strings() -> None:
    assert _check_chips_contract(["a?", "b?", "c?"]) is True


@pytest.mark.parametrize(
    "chips",
    [
        ["a?", "b?"],
        ["a?", "b?", "c?", "d?"],
        ["a?", "", "c?"],
        ["a?", "   ", "c?"],
        ["a?", "b?", 3],
        None,
        "chips",
    ],
)
def test_check_chips_contract_false_for_invalid_shapes(chips) -> None:
    assert _check_chips_contract(chips) is False


def test_has_exact_duplicate_detects_normalized_match() -> None:
    assert _has_exact_duplicate(["같은 질문?", "다른 질문?", " 같은 질문? "]) is True
    assert _has_exact_duplicate(["질문1?", "질문2?", "질문3?"]) is False


def test_evaluate_item_skips_judge_when_contract_violated() -> None:
    item = {
        "id": "C-001",
        "question": "q",
        "store": _STORE,
        "chips": ["a?", "b?"],
        "strategy_summary": "s",
        "strategy_actions": [],
    }

    result = _evaluate_item(item)

    assert result == {
        "id": "C-001",
        "contract_ok": False,
        "exact_duplicate": None,
        "scores": {},
        "judge_error": None,
        "judge_skipped_reason": "contract_violation",
    }


def _judge_payload(scores: dict[str, int] | None = None) -> str:
    scores = scores or {"관련성": 5, "비중복성": 4, "다양성": 4, "자연스러움": 5}
    return json.dumps(
        {
            criterion: {"score": score, "reason": "근거"}
            for criterion, score in scores.items()
        }
    )


@patch("models.shared.llm.call_llm")
def test_evaluate_item_calls_judge_once_when_contract_ok(mock_call_llm) -> None:
    mock_call_llm.return_value = (_judge_payload(), 50)
    item = {
        "id": "C-001",
        "question": "주변 경쟁사는 얼마나 되나요?",
        "store": _STORE,
        "chips": ["a?", "b?", "c?"],
        "strategy_summary": "요약",
        "strategy_actions": [{"type": "menu", "content": "행동"}],
    }

    result = _evaluate_item(item)

    assert result["contract_ok"] is True
    assert result["exact_duplicate"] is False
    assert result["scores"] == {"관련성": 5, "비중복성": 4, "다양성": 4, "자연스러움": 5}
    assert result["judge_error"] is None
    assert result["judge_skipped_reason"] is None
    mock_call_llm.assert_called_once()
    call_kwargs = mock_call_llm.call_args
    assert call_kwargs.args[0] == JUDGE_SYSTEM_PROMPT
    sent_payload = json.loads(call_kwargs.args[1])
    assert sent_payload["chips"] == ["a?", "b?", "c?"]
    assert sent_payload["strategy_summary"] == "요약"


@patch("models.shared.llm.call_llm")
def test_evaluate_item_catches_openai_error_per_item(mock_call_llm) -> None:
    request = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")
    response = httpx.Response(429, request=request)
    mock_call_llm.side_effect = openai.RateLimitError("limited", response=response, body=None)
    item = {
        "id": "C-001",
        "question": "q",
        "store": _STORE,
        "chips": ["a?", "b?", "c?"],
        "strategy_summary": "s",
        "strategy_actions": [],
    }

    result = _evaluate_item(item)

    assert result["contract_ok"] is True
    assert result["scores"] == {}
    assert result["judge_error"] == "rate_limit"
    assert result["judge_skipped_reason"] is None


@patch("models.shared.llm.call_llm")
def test_evaluate_item_catches_malformed_judge_json_per_item(mock_call_llm) -> None:
    mock_call_llm.return_value = ("이건 JSON이 아님", 10)
    item = {
        "id": "C-001",
        "question": "q",
        "store": _STORE,
        "chips": ["a?", "b?", "c?"],
        "strategy_summary": "s",
        "strategy_actions": [],
    }

    result = _evaluate_item(item)

    assert result["scores"] == {}
    assert result["judge_error"] == "invalid_response"


def test_build_report_computes_metrics_and_preserves_source_generation_model() -> None:
    results = [
        {
            "id": "C-001", "contract_ok": True, "exact_duplicate": False,
            "scores": {"관련성": 5, "비중복성": 5, "다양성": 5, "자연스러움": 5},
            "judge_error": None, "judge_skipped_reason": None,
        },
        {
            "id": "C-002", "contract_ok": True, "exact_duplicate": True,
            "scores": {"관련성": 3, "비중복성": 3, "다양성": 3, "자연스러움": 3},
            "judge_error": None, "judge_skipped_reason": None,
        },
        {
            "id": "C-003", "contract_ok": False, "exact_duplicate": None,
            "scores": {}, "judge_error": None, "judge_skipped_reason": "contract_violation",
        },
    ]
    source_header = _source_report(generation_model="gpt-4o-mini-2026-01-01")
    provenance = {"file": "report.json", "run_at": "2026-08-22T00:00:00+09:00", "sha256": "abc"}

    report = _build_report(
        results, excluded=[{"id": "C-999", "reason": "dataset_id_not_found"}],
        source_provenance=provenance, source_header=source_header,
        run_at=datetime(2026, 8, 23, 10, 0, tzinfo=ZoneInfo("Asia/Seoul")),
    )

    assert report["area"] == AREA
    assert report["run_at"] == "2026-08-23T10:00:00+09:00"
    assert report["generation_model"] == "gpt-4o-mini-2026-01-01"
    assert report["source_report"] == provenance
    assert report["metrics"]["contract_compliance"] == pytest.approx(2 / 3)
    assert report["metrics"]["exact_duplicate_rate"] == pytest.approx(1 / 2)
    assert report["metrics"]["relevance_avg"] == pytest.approx(4.0)
    assert report["metrics"]["non_redundancy_avg"] == pytest.approx(4.0)
    assert report["metrics"]["llm_judge_avg"] == pytest.approx(4.0)
    assert report["metrics"]["judge_failure_rate"] == pytest.approx(0.0)
    assert report["metrics"]["excluded_count"] == 1
    assert report["excluded"] == [{"id": "C-999", "reason": "dataset_id_not_found"}]


def test_source_provenance_hashes_actual_file_bytes(tmp_path) -> None:
    report_path = tmp_path / "report.json"
    report = _source_report()
    report_path.write_text(json.dumps(report), encoding="utf-8")

    provenance = _source_provenance(report_path, report)

    assert provenance["file"] == "report.json"
    assert provenance["run_at"] == report["run_at"]
    assert len(provenance["sha256"]) == 64


def test_evaluate_chips_raises_when_generation_model_mismatches_current_env(tmp_path) -> None:
    report_path = tmp_path / "report.json"
    report_path.write_text(
        json.dumps(_source_report(generation_model="다른-모델")), encoding="utf-8"
    )

    with pytest.raises(EvalPreflightError):
        evaluate_chips(report_path=report_path, dataset_path=tmp_path / "unused.json", limit=1)


def test_parse_args_requires_report() -> None:
    with pytest.raises(SystemExit):
        _parse_args(["--limit", "5"])


def test_parse_args_requires_limit_or_full() -> None:
    with pytest.raises(SystemExit):
        _parse_args(["--report", "r.json"])


def test_parse_args_accepts_full() -> None:
    args = _parse_args(["--report", "r.json", "--full"])

    assert args.report.name == "r.json"
    assert args.full is True
    assert args.limit is None
