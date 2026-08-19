# 컨설턴트 골든 데이터셋 평가기의 규칙 검사와 실행 흐름을 검증하는 테스트
import json
from datetime import datetime
from unittest.mock import patch
from zoneinfo import ZoneInfo

import pytest

from models.consult.eval.eval_strategy import (
    DEFAULT_STORE,
    _build_model_request,
    _build_report,
    _check_contract,
    _check_number_rules,
    _evaluate_item,
    _judge_response,
    evaluate_dataset,
)

_OK_RESPONSE = {
    "status": "ok",
    "title": "경쟁 상권 전략",
    "strategy": {
        "summary": "동일 업종이 많은 상권입니다.",
        "actions": [{"type": "menu", "content": "대표 메뉴를 알리세요."}],
    },
    "reasons": ["반경 내 동일 업종이 177곳입니다."],
    "sources": ["상권분석"],
    "tokens_used": 100,
    "suggested_chips": ["메뉴는요?", "홍보는요?", "단골은요?"],
}


def _item(item_id: str = "C-001") -> dict:
    return {
        "id": item_id,
        "area": "consult",
        "question": "주변 경쟁사는 얼마나 되나요?",
        "input": {
            "market_fixture": {
                "fixture_version": "v2-industry-code",
                "captured_at": "2026-08-18",
                "total_count": 6691,
                "same_industry_count": 177,
                "nearest_distance_m": 65,
            }
        },
        "expected": {
            "must_have_fields": [
                "title",
                "strategy",
                "reasons",
                "sources",
                "suggested_chips",
            ],
            "min_reasons": 1,
            "must_include_sources": ["상권분석"],
            "must_contain_number": True,
            "allowed_numbers": [6691, 177, 65],
            "number_scope": "reasons",
            "hallucination_check": "strict",
            "rubric": {
                "근거_충실도": "상권 정보를 근거로 활용했는가",
                "실행_가능성": "바로 실행할 수 있는가",
                "구체성": "가게와 상권에 맞는가",
                "자연스러움": "한국어가 자연스러운가",
            },
        },
    }


def test_build_model_request_injects_contract_fields_and_default_store() -> None:
    item = {
        "question": "주변 경쟁사는 얼마나 되나요?",
        "chatbot_type": "무시할 값",
        "user_id": 999,
    }

    request = _build_model_request(item)

    assert request == {
        "chatbot_type": "consultant",
        "user_id": 1,
        "question": "주변 경쟁사는 얼마나 되나요?",
        "store": DEFAULT_STORE,
        "extra": None,
    }


def test_build_model_request_uses_input_store_and_extra() -> None:
    store = {
        "name": "대관령 카페",
        "type": "카페",
        "address": "강원 평창군 대관령면",
        "lat": 37.6975,
        "lng": 128.7186,
    }
    item = {
        "question": "동네에 카페가 있나요?",
        "input": {"store": store, "extra": {"budget": "10만원"}},
    }

    request = _build_model_request(item)

    assert request["store"] == store
    assert request["extra"] == {"budget": "10만원"}


def test_check_contract_requires_fields_reason_count_and_sources() -> None:
    expected = {
        "must_have_fields": ["title", "strategy", "reasons", "sources"],
        "min_reasons": 2,
        "must_include_sources": ["상권분석"],
    }
    response = {
        "title": "경쟁 상권 전략",
        "strategy": {"summary": "요약", "actions": []},
        "reasons": ["근거 하나"],
        "sources": ["가게정보"],
    }

    assert _check_contract(response, expected) is False

    response["reasons"].append("근거 둘")
    response["sources"].append("상권분석")
    assert _check_contract(response, expected) is True


def test_check_number_rules_accepts_only_exact_whitelisted_values() -> None:
    expected = {
        "number_scope": "reasons",
        "allowed_numbers": [6691, 177, 65, -2, 12.5],
        "must_contain_number": True,
        "hallucination_check": "strict",
    }
    response = {
        "reasons": [
            "반경 내 전체 6,691곳 중 같은 업종은 177곳이며 최근접 거리는 65m입니다.",
            "변화율 -2와 지표 12.5를 함께 참고했습니다.",
        ]
    }

    passed, unexpected = _check_number_rules(response, expected)

    assert passed is True
    assert unexpected == []


def test_check_number_rules_reports_unexpected_number_without_tolerance() -> None:
    expected = {
        "number_scope": "reasons",
        "allowed_numbers": [177],
        "must_contain_number": True,
        "hallucination_check": "strict",
    }

    passed, unexpected = _check_number_rules(
        {"reasons": ["동일 업종이 약 177.1곳입니다."]},
        expected,
    )

    assert passed is False
    assert unexpected == [177.1]


def test_check_number_rules_rejects_missing_required_number() -> None:
    expected = {
        "number_scope": "reasons",
        "allowed_numbers": [177],
        "must_contain_number": True,
        "hallucination_check": "strict",
    }

    passed, unexpected = _check_number_rules(
        {"reasons": ["주변 경쟁이 많은 편입니다."]},
        expected,
    )

    assert passed is False
    assert unexpected == []


def test_check_number_rules_does_not_treat_bool_as_allowed_number() -> None:
    expected = {
        "number_scope": "reasons",
        "allowed_numbers": [True],
        "must_contain_number": True,
        "hallucination_check": "strict",
    }

    passed, unexpected = _check_number_rules(
        {"reasons": ["동일 업종 1곳입니다."]},
        expected,
    )

    assert passed is False
    assert unexpected == [1]


@patch("models.shared.llm.call_llm")
def test_judge_response_scores_all_rubric_keys_in_one_call(mock_call_llm) -> None:
    mock_call_llm.return_value = (
        json.dumps(
            {
                "근거_충실도": {"score": 5, "reason": "수치를 전략과 연결했습니다."},
                "실행_가능성": {"score": 4, "reason": "며칠 안에 실행할 수 있습니다."},
                "구체성": {"score": 4, "reason": "상권 조건을 반영했습니다."},
                "자연스러움": {"score": 5, "reason": "문장이 자연스럽습니다."},
            },
            ensure_ascii=False,
        ),
        80,
    )

    scores = _judge_response(_item(), _OK_RESPONSE)

    assert scores == {
        "근거_충실도": 5,
        "실행_가능성": 4,
        "구체성": 4,
        "자연스러움": 5,
    }
    mock_call_llm.assert_called_once()
    judge_input = json.loads(mock_call_llm.call_args.args[1])
    assert judge_input["store"] == DEFAULT_STORE


@patch("models.shared.llm.call_llm")
def test_judge_response_rejects_missing_reason(mock_call_llm) -> None:
    mock_call_llm.return_value = (
        json.dumps({"자연스러움": {"score": 5, "reason": ""}}, ensure_ascii=False),
        10,
    )
    item = _item()
    item["expected"]["rubric"] = {"자연스러움": "한국어가 자연스러운가"}

    with pytest.raises(ValueError, match="판정 근거"):
        _judge_response(item, _OK_RESPONSE)


@patch("models.shared.llm.call_llm")
@patch("models.consult.main.run")
def test_evaluate_item_patches_data_calls_and_removes_fixture_metadata(
    mock_run,
    mock_call_llm,
) -> None:
    def fake_run(_request: dict) -> dict:
        from models.consult.nodes import market_for_consult, trend_for_consult

        assert market_for_consult.get_market(0, 0) == {
            "total_count": 6691,
            "same_industry_count": 177,
            "nearest_distance_m": 65,
        }
        assert trend_for_consult.get_trend("카페") is None
        return _OK_RESPONSE

    mock_run.side_effect = fake_run
    mock_call_llm.return_value = (
        json.dumps(
            {
                key: {"score": 4, "reason": "평가 근거입니다."}
                for key in _item()["expected"]["rubric"]
            },
            ensure_ascii=False,
        ),
        50,
    )

    result = _evaluate_item(_item())

    assert result["passed"] is True
    assert result["context_snapshot"] == {
        "total_count": 6691,
        "same_industry_count": 177,
        "nearest_distance_m": 65,
    }
    assert result["_status_ok"] is True
    assert result["_contract_ok"] is True
    assert result["_latency_s"] >= 0


@patch("models.shared.llm.call_llm")
@patch("models.consult.main.run")
def test_evaluate_item_skips_judge_when_model_status_is_not_ok(mock_run, mock_call_llm) -> None:
    mock_run.return_value = {
        "status": "error",
        "reason": "provider_error",
        "message": "전략 생성 실패",
    }

    result = _evaluate_item(_item())

    assert result["passed"] is False
    assert result["scores"] == {}
    assert result["_status_ok"] is False
    mock_call_llm.assert_not_called()


def test_build_report_uses_required_schema_and_aggregates_metrics() -> None:
    results = [
        {
            "id": "C-001",
            "passed": True,
            "scores": {"근거_충실도": 4, "자연스러움": 4},
            "unexpected_numbers": [],
            "response": _OK_RESPONSE,
            "context_snapshot": {"same_industry_count": 177},
            "_status_ok": True,
            "_contract_ok": True,
            "_latency_s": 1.0,
        },
        {
            "id": "C-002",
            "passed": False,
            "scores": {"근거_충실도": 2, "자연스러움": 2},
            "unexpected_numbers": [9],
            "response": _OK_RESPONSE,
            "context_snapshot": {"same_industry_count": 0},
            "_status_ok": True,
            "_contract_ok": False,
            "_latency_s": 3.0,
        },
        {
            "id": "C-003",
            "passed": False,
            "scores": {},
            "unexpected_numbers": [],
            "response": {"status": "error"},
            "context_snapshot": {},
            "_status_ok": False,
            "_contract_ok": False,
            "_latency_s": 5.0,
        },
    ]
    run_at = datetime(2026, 8, 20, 18, 0, tzinfo=ZoneInfo("Asia/Seoul"))

    report = _build_report(results, area="consult", fixture_version="v2", run_at=run_at)

    assert list(report) == [
        "run_at",
        "area",
        "model",
        "dataset_version",
        "fixture_version",
        "item_count",
        "metrics",
        "items",
    ]
    assert report["run_at"] == "2026-08-20T18:00:00+09:00"
    assert report["item_count"] == 3
    assert report["metrics"] == {
        "llm_judge_avg": 3.0,
        "hallucination_rate": pytest.approx(1 / 3),
        "contract_compliance": pytest.approx(1 / 3),
        "failure_rate": pytest.approx(1 / 3),
        "latency_p50_s": 3.0,
        "latency_p95_s": 4.8,
    }
    assert set(report["items"][0]) == {
        "id",
        "passed",
        "scores",
        "unexpected_numbers",
        "response",
        "context_snapshot",
    }


@patch("models.consult.eval.eval_strategy.time.sleep")
@patch("models.consult.eval.eval_strategy._evaluate_item")
def test_evaluate_dataset_limits_count_sleeps_between_items_and_writes_report(
    mock_evaluate_item,
    mock_sleep,
    tmp_path,
) -> None:
    dataset = [_item("C-001"), _item("C-002"), _item("C-003")]
    dataset.append({"id": "B-001", "area": "basic"})
    dataset_path = tmp_path / "golden.json"
    dataset_path.write_text(json.dumps(dataset, ensure_ascii=False), encoding="utf-8")

    def result_for(item: dict) -> dict:
        return {
            "id": item["id"],
            "passed": True,
            "scores": {"자연스러움": 4},
            "unexpected_numbers": [],
            "response": _OK_RESPONSE,
            "context_snapshot": {"same_industry_count": 177},
            "_status_ok": True,
            "_contract_ok": True,
            "_latency_s": 1.0,
        }

    mock_evaluate_item.side_effect = result_for

    report, report_path = evaluate_dataset(
        dataset_path=dataset_path,
        area="consult",
        limit=2,
        report_dir=tmp_path / "reports",
    )

    assert report["item_count"] == 2
    assert [item["id"] for item in report["items"]] == ["C-001", "C-002"]
    assert json.loads(report_path.read_text(encoding="utf-8"))["item_count"] == 2
    mock_sleep.assert_called_once_with(1.0)


def test_evaluate_dataset_rejects_non_positive_limit(tmp_path) -> None:
    dataset_path = tmp_path / "golden.json"
    dataset_path.write_text("[]", encoding="utf-8")

    with pytest.raises(ValueError, match="양수"):
        evaluate_dataset(dataset_path=dataset_path, limit=0, report_dir=tmp_path)
