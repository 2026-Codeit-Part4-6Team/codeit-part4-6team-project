# 컨설턴트 골든 데이터셋 평가기의 규칙 검사와 실행 흐름을 검증하는 테스트
import json
from datetime import datetime
from unittest.mock import MagicMock, patch
from zoneinfo import ZoneInfo

import httpx
import openai
import pytest

from models.consult.eval.eval_strategy import (
    DEFAULT_DATASET_PATH,
    DEFAULT_STORE,
    _build_model_request,
    _build_report,
    _check_contract,
    _check_number_rules,
    _evaluate_item,
    _judge_market_fixture,
    _judge_response,
    _parse_args,
    _run_graph,
    _sanitize_trend_fixture,
    _trend_fixture_version,
    check_trend_path,
    evaluate_dataset,
    main,
    trend_path_match_rate,
)
from models.shared.config import OPENAI_JUDGE_MODEL, OPENAI_MODEL

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
            },
            "trend_fixture": None,
        },
        "expected": {
            "trend_used": False,
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


def test_sanitize_trend_fixture_removes_metadata_and_keeps_api_payload() -> None:
    item = _item()
    item["input"]["trend_fixture"] = {
        "fixture_version": "v1-naver-apihub",
        "captured_at": "2026-08-19",
        "keyword": "탕후루",
        "direction": "상승",
        "related": ["구슬아이스크림"],
        "weather": None,
    }

    assert _sanitize_trend_fixture(item) == {
        "keyword": "탕후루",
        "direction": "상승",
        "related": ["구슬아이스크림"],
        "weather": None,
    }


def test_sanitize_trend_fixture_preserves_explicit_null() -> None:
    assert _sanitize_trend_fixture(_item()) is None


def test_trend_fixture_version_uses_non_null_fixture_version() -> None:
    null_item = _item("C-001")
    trend_item = _item("C-046")
    trend_item["input"]["trend_fixture"] = {
        "fixture_version": "v1-naver-apihub",
        "captured_at": "2026-08-19",
        "keyword": "탕후루",
        "direction": "상승",
        "related": [],
        "weather": None,
    }

    assert _trend_fixture_version([null_item, trend_item]) == "v1-naver-apihub"


@patch("models.consult.eval.eval_strategy.assemble_response")
@patch("models.consult.eval.eval_strategy.build_consultant")
@patch("models.consult.eval.eval_strategy.build_initial_state")
def test_run_graph_invokes_graph_once_and_returns_final_state_and_response(
    mock_build_initial_state,
    mock_build_consultant,
    mock_assemble_response,
) -> None:
    graph = MagicMock()
    final_state = {"status": "ok", "context": {"market": {"total_count": 6691}}}
    response = dict(_OK_RESPONSE)
    graph.invoke.return_value = final_state
    mock_build_consultant.return_value = graph
    mock_assemble_response.return_value = response
    expected_initial_state = {
        "chatbot_type": "consultant",
        "user_id": 1,
        "question": "주변 경쟁사는 얼마나 되나요?",
        "store": DEFAULT_STORE,
        "extra": {},
        "tokens_used": 0,
    }
    mock_build_initial_state.return_value = expected_initial_state
    request = _build_model_request(_item())

    actual_state, actual_response = _run_graph(request)

    assert actual_state == final_state
    assert actual_response == response
    mock_build_initial_state.assert_called_once_with(request)
    graph.invoke.assert_called_once_with(expected_initial_state)
    mock_assemble_response.assert_called_once_with(final_state)


def test_check_trend_path_compares_expected_keyword_path_and_context() -> None:
    item = _item()
    item["expected"]["trend_used"] = True

    result = check_trend_path(
        item,
        {
            "context": {
                "question_analysis": {"keyword": "탕후루"},
                "trend": {"keyword": "탕후루", "direction": "상승"},
            }
        },
    )

    assert result == {
        "expected": True,
        "actual": True,
        "matched": True,
        "keyword": "탕후루",
        "trend_in_context": True,
    }


def test_check_trend_path_reports_mismatch_without_failing_item() -> None:
    item = _item()

    result = check_trend_path(
        item,
        {"context": {"question_analysis": {"keyword": "탕후루"}}},
    )

    assert result["matched"] is False
    assert result["expected"] is False
    assert result["actual"] is True
    assert result["trend_in_context"] is False


def test_trend_path_match_rate_ignores_results_without_path_check() -> None:
    results = [
        {"trend_path": {"matched": True}},
        {"trend_path": None},
        {"trend_path": {"matched": False}},
    ]

    assert trend_path_match_rate(results) == 0.5
    assert trend_path_match_rate([{"trend_path": None}]) == 1.0


def test_judge_market_fixture_strips_industry_breakdown_but_keeps_density_tier() -> None:
    """생성 모델은 industry_breakdown을 본 적이 없다(D5, strategy.py _market_section에서
    제외) — Judge에게 그대로 넘기면 둘의 입력 조건이 달라진다. density_tier는 실제로
    프롬프트에 포함되므로(strategy.py:106) 그대로 유지한다."""
    market = {
        "total_count": 6691,
        "same_industry_count": 177,
        "nearest_distance_m": 65,
        "density_tier": "높음",
        "industry_breakdown": {"한식": 39, "카페": 33},
    }

    filtered = _judge_market_fixture(market)

    assert "industry_breakdown" not in filtered
    assert filtered["density_tier"] == "높음"
    assert filtered["total_count"] == 6691


def test_judge_market_fixture_passes_through_none_and_empty() -> None:
    assert _judge_market_fixture(None) is None
    assert _judge_market_fixture({}) == {}


@patch("models.shared.llm.call_llm")
def test_judge_response_scores_all_rubric_keys_in_one_call(mock_call_llm) -> None:
    item = _item()
    item["input"]["trend_fixture"] = {
        "fixture_version": "v1-naver-apihub",
        "captured_at": "2026-08-19",
        "keyword": "탕후루",
        "direction": "상승",
        "related": ["구슬아이스크림"],
        "weather": None,
    }
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

    context_snapshot = {
        "market": {"same_industry_count": 177},
        "trend": {
            "keyword": "탕후루",
            "direction": "상승",
            "related": ["구슬아이스크림"],
            "weather": None,
        },
    }

    scores = _judge_response(item, _OK_RESPONSE, context_snapshot)

    assert scores == {
        "근거_충실도": 5,
        "실행_가능성": 4,
        "구체성": 4,
        "자연스러움": 5,
    }
    mock_call_llm.assert_called_once()
    judge_input = json.loads(mock_call_llm.call_args.args[1])
    assert judge_input["store"] == DEFAULT_STORE
    assert judge_input["market_fixture"] == {"same_industry_count": 177}
    assert judge_input["trend_fixture"] == {
        "keyword": "탕후루",
        "direction": "상승",
        "related": ["구슬아이스크림"],
        "weather": None,
    }
    assert mock_call_llm.call_args.kwargs == {
        "json_mode": True,
        "model": OPENAI_JUDGE_MODEL,
    }


@patch("models.shared.llm.call_llm")
def test_judge_response_rejects_missing_reason(mock_call_llm) -> None:
    mock_call_llm.return_value = (
        json.dumps({"자연스러움": {"score": 5, "reason": ""}}, ensure_ascii=False),
        10,
    )
    item = _item()
    item["expected"]["rubric"] = {"자연스러움": "한국어가 자연스러운가"}

    with pytest.raises(ValueError, match="판정 근거"):
        _judge_response(item, _OK_RESPONSE, {"market": {}, "trend": None})


@patch("models.shared.llm.call_llm")
@patch("models.consult.eval.eval_strategy._run_graph")
def test_evaluate_item_patches_data_calls_and_removes_fixture_metadata(
    mock_run_graph,
    mock_call_llm,
) -> None:
    item = _item()
    item["input"]["trend_fixture"] = {
        "fixture_version": "v1-naver-apihub",
        "captured_at": "2026-08-19",
        "keyword": "탕후루",
        "direction": "상승",
        "related": ["구슬아이스크림"],
        "weather": None,
    }
    item["expected"]["trend_used"] = True
    response = {**_OK_RESPONSE, "sources": ["상권분석", "트렌드"]}
    context_snapshot = {
        "question_analysis": {"keyword": "탕후루"},
        "market": {
            "total_count": 6691,
            "same_industry_count": 177,
            "nearest_distance_m": 65,
            "density_tier": "높음",
        },
        "trend": {
            "keyword": "탕후루",
            "direction": "상승",
            "related": ["구슬아이스크림"],
            "weather": None,
        },
    }

    def fake_run_graph(_request: dict) -> tuple[dict, dict]:
        from models.consult.nodes import market_for_consult, trend_for_consult

        assert market_for_consult.get_market(0, 0) == {
            "total_count": 6691,
            "same_industry_count": 177,
            "nearest_distance_m": 65,
        }
        assert trend_for_consult.get_trend("탕후루") == {
            "keyword": "탕후루",
            "direction": "상승",
            "related": ["구슬아이스크림"],
            "weather": None,
        }
        return {"context": context_snapshot}, response

    mock_run_graph.side_effect = fake_run_graph
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

    result = _evaluate_item(item)

    assert result["passed"] is True
    assert result["context_snapshot"] == context_snapshot
    assert result["trend_path"] == {
        "expected": True,
        "actual": True,
        "matched": True,
        "keyword": "탕후루",
        "trend_in_context": True,
    }
    assert result["_status_ok"] is True
    assert result["_contract_ok"] is True
    assert result["_judge_ok"] is True
    assert result["judge_error"] is None
    assert result["_latency_s"] >= 0


@patch("models.consult.clients.trend_api.fetch")
@patch("models.consult.clients.market_api.fetch")
@patch("models.shared.llm.call_llm")
@patch("models.consult.eval.eval_strategy._run_graph")
def test_evaluate_item_never_reaches_live_market_or_trend_api(
    mock_run_graph,
    mock_call_llm,
    mock_market_fetch,
    mock_trend_fetch,
) -> None:
    """market_for_consult/trend_for_consult 노드 패치가 걸려 있으면 그 아래 실제
    API 클라이언트(market_api.fetch/trend_api.fetch)는 절대 호출되지 않아야 한다.
    나중에 패치 대상 경로가 바뀌어도(예: 캐시 계층을 우회하는 리팩터링) 이 테스트가
    실제 네트워크 호출을 규제한다(D-169 — 평가 중 외부 API 호출 금지)."""
    item = _item()
    item["input"]["trend_fixture"] = {
        "fixture_version": "v1-naver-apihub",
        "captured_at": "2026-08-19",
        "keyword": "탕후루",
        "direction": "상승",
        "related": [],
        "weather": None,
    }
    item["expected"]["trend_used"] = True

    def fake_run_graph(_request: dict) -> tuple[dict, dict]:
        from models.consult.nodes import market_for_consult, trend_for_consult

        market_for_consult.get_market(0, 0)
        trend_for_consult.get_trend("탕후루")
        return {"context": {"market": {}, "trend": {}}}, _OK_RESPONSE

    mock_run_graph.side_effect = fake_run_graph
    mock_call_llm.return_value = (
        json.dumps(
            {key: {"score": 4, "reason": "근거"} for key in _item()["expected"]["rubric"]},
            ensure_ascii=False,
        ),
        50,
    )

    _evaluate_item(item)

    mock_market_fetch.assert_not_called()
    mock_trend_fetch.assert_not_called()


@patch("models.shared.llm.call_llm")
@patch("models.consult.eval.eval_strategy._run_graph")
def test_evaluate_item_hides_graph_exception_and_skips_judge(
    mock_run_graph,
    mock_call_llm,
) -> None:
    mock_run_graph.side_effect = RuntimeError("비밀 provider detail")

    result = _evaluate_item(_item())

    assert result["passed"] is False
    assert result["scores"] == {}
    assert result["_status_ok"] is False
    assert result["_judge_ok"] is None
    assert result["judge_error"] is None
    assert result["trend_path"] is None
    assert result["response"] == {
        "status": "error",
        "reason": "unknown",
        "message": "전략 생성 중 오류가 발생했습니다.",
    }
    assert "비밀" not in json.dumps(result, ensure_ascii=False)
    mock_call_llm.assert_not_called()


@patch("models.shared.llm.call_llm")
@patch("models.consult.eval.eval_strategy._run_graph")
def test_evaluate_item_preserves_response_when_judge_returns_invalid_json(
    mock_run_graph,
    mock_call_llm,
) -> None:
    final_state = {
        "context": {
            "question_analysis": {"keyword": None},
            "market": {
                "total_count": 6691,
                "same_industry_count": 177,
                "nearest_distance_m": 65,
                "density_tier": "높음",
            },
            "trend": None,
        }
    }
    mock_run_graph.return_value = (final_state, _OK_RESPONSE)
    mock_call_llm.return_value = ("JSON이 아닌 응답", 10)

    result = _evaluate_item(_item())

    assert result["passed"] is False
    assert result["response"] == _OK_RESPONSE
    assert result["scores"] == {}
    assert result["judge_error"] == "invalid_response"
    assert result["_status_ok"] is True
    assert result["_contract_ok"] is True
    assert result["_judge_ok"] is False


@patch("models.shared.llm.call_llm")
@patch("models.consult.eval.eval_strategy._run_graph")
def test_evaluate_item_classifies_judge_rate_limit_and_continues(
    mock_run_graph,
    mock_call_llm,
) -> None:
    final_state = {
        "context": {
            "question_analysis": {"keyword": None},
            "market": {"same_industry_count": 177},
            "trend": None,
        }
    }
    mock_run_graph.return_value = (final_state, _OK_RESPONSE)
    request = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")
    response = httpx.Response(429, request=request)
    mock_call_llm.side_effect = openai.RateLimitError(
        "rate limited",
        response=response,
        body=None,
    )

    result = _evaluate_item(_item())

    assert result["passed"] is False
    assert result["response"] == _OK_RESPONSE
    assert result["judge_error"] == "rate_limit"
    assert result["_judge_ok"] is False


def test_build_report_uses_required_schema_and_aggregates_metrics() -> None:
    results = [
        {
            "id": "C-001",
            "passed": True,
            "scores": {"근거_충실도": 4, "자연스러움": 4},
            "unexpected_numbers": [],
            "response": _OK_RESPONSE,
            "context_snapshot": {"same_industry_count": 177},
            "trend_path": {
                "expected": False,
                "actual": False,
                "matched": True,
                "keyword": None,
                "trend_in_context": False,
            },
            "judge_error": None,
            "_status_ok": True,
            "_contract_ok": True,
            "_judge_ok": True,
            "_latency_s": 1.0,
        },
        {
            "id": "C-002",
            "passed": False,
            "scores": {"근거_충실도": 2, "자연스러움": 2},
            "unexpected_numbers": [9],
            "response": _OK_RESPONSE,
            "context_snapshot": {"same_industry_count": 0},
            "trend_path": {
                "expected": True,
                "actual": False,
                "matched": False,
                "keyword": None,
                "trend_in_context": False,
            },
            "judge_error": "invalid_response",
            "_status_ok": True,
            "_contract_ok": False,
            "_judge_ok": False,
            "_latency_s": 3.0,
        },
        {
            "id": "C-003",
            "passed": False,
            "scores": {},
            "unexpected_numbers": [],
            "response": {"status": "error"},
            "context_snapshot": {},
            "trend_path": None,
            "judge_error": None,
            "_status_ok": False,
            "_contract_ok": False,
            "_judge_ok": None,
            "_latency_s": 5.0,
        },
    ]
    run_at = datetime(2026, 8, 20, 18, 0, tzinfo=ZoneInfo("Asia/Seoul"))

    report = _build_report(
        results,
        area="consult",
        fixture_version="v2",
        trend_fixture_version="v1-naver-apihub",
        run_at=run_at,
    )

    assert list(report) == [
        "run_at",
        "area",
        "generation_model",
        "judge_model",
        "dataset_version",
        "fixture_version",
        "trend_fixture_version",
        "item_count",
        "metrics",
        "items",
    ]
    assert report["run_at"] == "2026-08-20T18:00:00+09:00"
    assert report["generation_model"] == OPENAI_MODEL
    assert report["judge_model"] == OPENAI_JUDGE_MODEL
    assert report["dataset_version"] == "v1.3"
    assert report["trend_fixture_version"] == "v1-naver-apihub"
    assert report["item_count"] == 3
    assert report["metrics"] == {
        "llm_judge_avg": 3.0,
        "hallucination_rate": pytest.approx(1 / 3),
        "contract_compliance": pytest.approx(1 / 3),
        "trend_path_match_rate": 0.5,
        "judge_failure_rate": 0.5,
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
        "trend_path",
        "judge_error",
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
            "trend_path": {
                "expected": False,
                "actual": False,
                "matched": True,
                "keyword": None,
                "trend_in_context": False,
            },
            "judge_error": None,
            "_status_ok": True,
            "_contract_ok": True,
            "_judge_ok": True,
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
    assert report["trend_fixture_version"] == "unknown"
    assert report["metrics"]["trend_path_match_rate"] == 1.0
    assert [item["id"] for item in report["items"]] == ["C-001", "C-002"]
    assert json.loads(report_path.read_text(encoding="utf-8"))["item_count"] == 2
    assert report_path.name.endswith("_consult_limit-2.json")
    mock_sleep.assert_called_once_with(1.0)


@patch("models.consult.eval.eval_strategy._evaluate_item")
def test_evaluate_dataset_keeps_two_reports_created_on_same_day(
    mock_evaluate_item,
    tmp_path,
) -> None:
    dataset_path = tmp_path / "golden.json"
    dataset_path.write_text(json.dumps([_item()], ensure_ascii=False), encoding="utf-8")
    mock_evaluate_item.return_value = {
        "id": "C-001",
        "passed": True,
        "scores": {"자연스러움": 4},
        "unexpected_numbers": [],
        "response": _OK_RESPONSE,
        "context_snapshot": {"market": {"same_industry_count": 177}},
        "trend_path": {
            "expected": False,
            "actual": False,
            "matched": True,
            "keyword": None,
            "trend_in_context": False,
        },
        "judge_error": None,
        "_status_ok": True,
        "_contract_ok": True,
        "_judge_ok": True,
        "_latency_s": 1.0,
    }
    run_times = [
        datetime(2026, 8, 20, 18, 0, 0, 123456, tzinfo=ZoneInfo("Asia/Seoul")),
        datetime(2026, 8, 20, 18, 0, 1, 654321, tzinfo=ZoneInfo("Asia/Seoul")),
    ]

    with patch("models.consult.eval.eval_strategy.datetime") as mock_datetime:
        mock_datetime.now.side_effect = run_times
        _, first_path = evaluate_dataset(
            dataset_path=dataset_path,
            area="consult",
            limit=1,
            report_dir=tmp_path / "reports",
        )
        _, second_path = evaluate_dataset(
            dataset_path=dataset_path,
            area="consult",
            limit=1,
            report_dir=tmp_path / "reports",
        )

    assert first_path.name == "2026-08-20_180000_123456_consult_limit-1.json"
    assert second_path.name == "2026-08-20_180001_654321_consult_limit-1.json"
    assert first_path != second_path
    assert first_path.exists()
    assert second_path.exists()


@patch("models.consult.eval.eval_strategy.time.sleep")
@patch("models.consult.eval.eval_strategy._evaluate_item")
def test_evaluate_dataset_keeps_prior_item_result_after_later_judge_failure(
    mock_evaluate_item,
    _mock_sleep,
    tmp_path,
) -> None:
    """한 문항의 Judge 호출이 실패해도(_evaluate_item이 예외를 던지지 않고 실패
    dict를 반환하는 실제 계약) 배치 전체가 죽지 않고, 앞서 성공한 문항 결과가
    리포트에 그대로 남아 있어야 한다 — 여기서 죽으면 그때까지 쓴 LLM 비용이 전부
    버려진다(§10.5)."""
    dataset = [_item("C-001"), _item("C-002")]
    dataset_path = tmp_path / "golden.json"
    dataset_path.write_text(json.dumps(dataset, ensure_ascii=False), encoding="utf-8")

    def fake_evaluate_item(item: dict) -> dict:
        base = {
            "id": item["id"],
            "scores": {"자연스러움": 4},
            "unexpected_numbers": [],
            "response": _OK_RESPONSE,
            "context_snapshot": {"market": {"same_industry_count": 177}},
            "trend_path": None,
            "_status_ok": True,
            "_contract_ok": True,
            "_latency_s": 1.0,
        }
        if item["id"] == "C-001":
            return {**base, "passed": True, "judge_error": None, "_judge_ok": True}
        return {**base, "passed": False, "judge_error": "rate_limit", "_judge_ok": False}

    mock_evaluate_item.side_effect = fake_evaluate_item

    report, report_path = evaluate_dataset(
        dataset_path=dataset_path,
        area="consult",
        limit=2,
        report_dir=tmp_path / "reports",
    )

    assert [item["id"] for item in report["items"]] == ["C-001", "C-002"]
    assert report["items"][0]["passed"] is True
    assert report["items"][1]["judge_error"] == "rate_limit"
    assert report["item_count"] == 2
    assert report_path.exists()


def test_evaluate_dataset_rejects_non_positive_limit(tmp_path) -> None:
    dataset_path = tmp_path / "golden.json"
    dataset_path.write_text("[]", encoding="utf-8")

    with pytest.raises(ValueError, match="양수"):
        evaluate_dataset(dataset_path=dataset_path, limit=0, report_dir=tmp_path)


def test_parse_args_requires_explicit_limit_or_full() -> None:
    with pytest.raises(SystemExit):
        _parse_args([])

    with pytest.raises(SystemExit):
        _parse_args(["--limit", "2", "--full"])


def test_parse_args_accepts_limit_and_full_as_separate_modes() -> None:
    limited = _parse_args(["--limit", "2"])
    full = _parse_args(["--full"])

    assert limited.limit == 2
    assert limited.full is False
    assert full.limit is None
    assert full.full is True


@patch("models.consult.eval.eval_strategy.evaluate_dataset")
def test_main_runs_full_evaluation_only_with_explicit_full_flag(
    mock_evaluate_dataset,
    tmp_path,
) -> None:
    report_path = tmp_path / "full.json"
    mock_evaluate_dataset.return_value = ({}, report_path)

    exit_code = main(["--full"])

    assert exit_code == 0
    mock_evaluate_dataset.assert_called_once_with(
        dataset_path=DEFAULT_DATASET_PATH,
        area="consult",
        limit=None,
    )


@patch("models.consult.eval.eval_strategy.evaluate_dataset")
def test_main_returns_one_and_logs_when_evaluation_fails(
    mock_evaluate_dataset,
    caplog,
) -> None:
    mock_evaluate_dataset.side_effect = RuntimeError("evaluation failed")

    exit_code = main(["--limit", "1"])

    assert exit_code == 1
    assert "컨설턴트 골든 데이터셋 평가 실패" in caplog.text
