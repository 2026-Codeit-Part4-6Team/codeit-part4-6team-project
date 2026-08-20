# 컨설턴트 전략 응답을 골든 데이터셋 기준으로 평가하는 실행 스크립트
"""컨설턴트 골든 데이터셋의 규칙 기반 검사와 LLM Judge 실행을 담당한다."""

import argparse
import json
import logging
import re
import time
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any
from unittest.mock import patch
from zoneinfo import ZoneInfo

import openai

from models.consult.graph.build_consultant import build_consultant
from models.consult.main import assemble_response, build_initial_state
from models.shared import llm as shared_llm
from models.shared.config import OPENAI_JUDGE_MODEL, OPENAI_MODEL
from models.shared.llm_errors import classify_llm_error

EVAL_USER_ID = 1
DATASET_VERSION = "v1.3"
DEFAULT_DATASET_PATH = Path("shared_data/golden_dataset.json")
DEFAULT_REPORT_DIR = Path(__file__).resolve().parent / "reports"
SLEEP_SECONDS = 1.0
DEFAULT_STORE = {
    "name": "카페 코드잇",
    "type": "카페",
    "address": "서울 강남구 역삼동",
    "lat": 37.4979,
    "lng": 127.0276,
}

_NUMBER_PATTERN = re.compile(r"(?<![\d.,])[-+]?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?(?![\d.,])")

logger = logging.getLogger(__name__)

JUDGE_SYSTEM_PROMPT = """당신은 소상공인 컨설턴트 챗봇 응답 평가자입니다.
요청된 평가 항목만 1~5점으로 채점하고 각 항목에 판정 근거 한 문장을 작성하세요.
반드시 다음 JSON 객체 형식으로만 답하세요.
{"평가항목": {"score": 1, "reason": "판정 근거 한 문장"}}

① 근거_충실도 — reasons가 주어진 상권 정보를 정확하고 논리적으로 활용했는가
1점: 주어진 상권 정보를 사용하지 않고 막연하거나 확인할 수 없는 주장만 함
2점: 상권 정보를 언급하지만 질문이나 제안과 관련이 없거나 의미를 잘못 해석함
3점: fixture의 수치를 정확히 인용하지만 단순 나열에 그쳐 전략과의 연결이 부족함
4점: 질문과 관련된 fixture 수치를 선택해 전략의 근거로 자연스럽게 연결함
5점: 가장 관련 있는 상권 정보를 정확히 활용하고, 과도한 단정 없이 왜 전략의 근거가
되는지 설득력 있게 설명함

② 실행_가능성 — actions를 소상공인이 실제 영업 환경에서 실행할 수 있는가
1점: 실행 항목이 없거나 "마케팅을 강화하세요" 수준의 추상적인 방향만 제시함
2점: 무엇을 할지는 제시하지만 구체적인 실행 방법이 없음
3점: 실행할 행동은 식별할 수 있으나 대상·방법·채널·시점 중 중요한 정보가 빠져 있음
4점: 무엇을 어떻게 할지가 명확하고, 큰 비용이나 전문 인력 없이 며칠 내 시도할 수 있음
5점: 무엇을·어떻게·어떤 순서나 시점에 실행할지가 명확해 오늘이나 다음 영업일부터
바로 적용할 수 있음

③ 구체성 — 제안이 주어진 가게 정보와 상권 조건에 맞게 구체화되었는가
1점: 업종이나 상권과 관계없이 어떤 가게에도 적용되는 일반적인 조언임
2점: 업종만 반영했으며 상권이나 질문의 구체적인 조건은 반영하지 않음
3점: 가게 정보나 상권 정보 일부를 반영했지만 핵심 제안은 여전히 일반적임
4점: 업종과 상권 조건이 실제 행동 제안에 반영되어 맞춤형 답변으로 볼 수 있음
5점: 질문·업종·상권의 핵심 조건을 함께 연결하고, 왜 이 가게에 이 전략이 적합한지도
구체적으로 설명함

④ 자연스러움 — summary·actions·reasons가 한국어로 자연스럽고 이해하기 쉬운가
1점: 문장이 끊기거나 번역투가 심해 의미를 이해하기 어려움
2점: 의미는 이해되지만 딱딱한 번역투·기계적인 표현·반복이 자주 나타남
3점: 전반적으로 이해하기 쉽지만 일부 어색한 표현이나 불필요한 반복이 있음
4점: 문장 연결이 매끄럽고 소상공인이 쉽게 이해할 수 있는 자연스러운 표현을 사용함
5점: 전문성과 친근함의 균형이 좋고, 불필요한 반복이나 어려운 용어 없이 실제
컨설턴트의 설명처럼 명확하고 자연스러움

채점 범위는 근거_충실도는 reasons, 실행_가능성은 actions, 구체성은 summary와 actions,
자연스러움은 summary·actions·reasons 전체입니다. 숫자의 fixture 일치 여부는 별도 규칙
검사가 담당하므로 숫자를 어떻게 해석하고 전략과 연결했는지만 평가하세요.
"""


def _build_model_request(item: dict) -> dict:
    """골든 문항을 컨설턴트 ModelRequest 계약으로 조립한다."""
    raw = item.get("input") or {}
    return {
        "chatbot_type": "consultant",
        "user_id": EVAL_USER_ID,
        "question": item["question"],
        "store": raw.get("store", DEFAULT_STORE),
        "extra": raw.get("extra"),
    }


def _check_contract(response: dict, expected: dict) -> bool:
    """필수 필드, 근거 개수, 필수 출처가 응답 계약을 만족하는지 확인한다."""
    if any(field not in response for field in expected.get("must_have_fields", [])):
        return False

    reasons = response.get("reasons")
    if not isinstance(reasons, list) or len(reasons) < expected.get("min_reasons", 0):
        return False

    sources = response.get("sources")
    if not isinstance(sources, list):
        return False
    return all(source in sources for source in expected.get("must_include_sources", []))


def _check_number_rules(response: dict, expected: dict) -> tuple[bool, list[int | float]]:
    """지정 범위의 숫자가 존재하고 G-08 허용 목록을 정확히 따르는지 확인한다."""
    scope = expected.get("number_scope", "reasons")
    extracted = _extract_numbers(response.get(scope))
    allowed = {
        normalized
        for value in expected.get("allowed_numbers", [])
        if (normalized := _normalize_number(value)) is not None
    }
    unexpected = []
    seen = set()
    for normalized, original in extracted:
        if normalized not in allowed and normalized not in seen:
            unexpected.append(original)
            seen.add(normalized)

    has_required_number = not expected.get("must_contain_number") or bool(extracted)
    strict_ok = expected.get("hallucination_check") != "strict" or not unexpected
    return has_required_number and strict_ok, unexpected


def _extract_numbers(value: Any) -> list[tuple[Decimal, int | float]]:
    """문자열 또는 문자열 목록에서 비교용 Decimal과 JSON 저장용 숫자를 뽑는다."""
    numbers = []
    for text in _iter_text(value):
        for match in _NUMBER_PATTERN.findall(text):
            normalized = Decimal(match.replace(",", ""))
            original = (
                int(normalized) if normalized == normalized.to_integral() else float(normalized)
            )
            numbers.append((normalized, original))
    return numbers


def _iter_text(value: Any):
    """숫자 검사 범위의 중첩 목록에서 문자열만 순서대로 순회한다."""
    if isinstance(value, str):
        yield value
    elif isinstance(value, (list, tuple)):
        for item in value:
            yield from _iter_text(item)


def _normalize_number(value: Any) -> Decimal | None:
    """허용 숫자를 유한한 Decimal로 바꾸되 bool과 비숫자는 제외한다."""
    if isinstance(value, bool) or not isinstance(value, (int, float, Decimal)):
        return None
    try:
        normalized = Decimal(str(value))
    except InvalidOperation:
        return None
    return normalized if normalized.is_finite() else None


def _sanitize_market_fixture(item: dict) -> dict:
    """평가용 상권 fixture에서 결과 메타데이터만 제거한다."""
    raw = item.get("input") or {}
    fixture = raw.get("market_fixture") or {}
    return {
        key: value
        for key, value in fixture.items()
        if key not in {"fixture_version", "captured_at"}
    }


def _sanitize_trend_fixture(item: dict) -> dict | None:
    """평가용 트렌드 fixture에서 결과 메타데이터를 제거하고 null은 유지한다."""
    raw = item.get("input") or {}
    fixture = raw.get("trend_fixture")
    if not fixture:
        return None
    return {
        key: value
        for key, value in fixture.items()
        if key not in {"fixture_version", "captured_at"}
    }


def _run_graph(request: dict) -> tuple[dict, dict]:
    """평가용으로 그래프를 한 번 실행해 최종 state와 서비스 응답을 함께 반환한다."""
    initial_state = build_initial_state(request)
    final_state = build_consultant().invoke(initial_state)
    return final_state, assemble_response(final_state)


def check_trend_path(item: dict, final_state: dict) -> dict:
    """기대된 트렌드 경로와 질문 분석 노드가 실제 선택한 경로를 비교한다."""
    context = final_state.get("context") or {}
    analysis = context.get("question_analysis") or {}
    keyword = analysis.get("keyword")
    expected = item["expected"]["trend_used"]
    actual = keyword is not None
    return {
        "expected": expected,
        "actual": actual,
        "matched": expected == actual,
        "keyword": keyword,
        "trend_in_context": bool(context.get("trend")),
    }


def trend_path_match_rate(item_results: list[dict]) -> float:
    """실행 결과 중 트렌드 경로 검사가 있는 문항의 일치율을 계산한다."""
    checks = [result["trend_path"] for result in item_results if result.get("trend_path")]
    if not checks:
        return 1.0
    return sum(check["matched"] for check in checks) / len(checks)


def _judge_market_fixture(market: dict | None) -> dict | None:
    """Judge에게는 생성 모델이 실제로 본 필드만 넘긴다.

    industry_breakdown은 strategy.py의 _market_section()에서 제외돼 있어(D5, 1000건
    페이지 상한으로 대형 상권에서 부정확) 생성 모델이 본 적 없는 정보다 — 그대로 Judge에게
    넘기면 생성 모델과 Judge가 서로 다른 입력을 보게 된다. density_tier는 실제로
    프롬프트에 포함되므로(밀도 등급) 그대로 둔다.
    """
    if not market:
        return market
    return {key: value for key, value in market.items() if key != "industry_breakdown"}


def _judge_response(
    item: dict,
    response: dict,
    context_snapshot: dict,
) -> dict[str, int]:
    """문항의 rubric 전체를 LLM 한 번으로 채점하고 점수만 반환한다."""
    rubric = (item.get("expected") or {}).get("rubric") or {}
    judge_input = {
        "question": item["question"],
        "store": _build_model_request(item)["store"],
        "rubric": rubric,
        "market_fixture": _judge_market_fixture(context_snapshot.get("market")),
        "trend_fixture": context_snapshot.get("trend"),
        "response": response,
    }
    raw, _ = shared_llm.call_llm(
        JUDGE_SYSTEM_PROMPT,
        json.dumps(judge_input, ensure_ascii=False),
        json_mode=True,
        model=OPENAI_JUDGE_MODEL,
    )
    parsed = json.loads(raw)
    if not isinstance(parsed, dict):
        raise TypeError("LLM Judge 응답은 JSON 객체여야 합니다.")

    scores = {}
    for criterion in rubric:
        judgement = parsed.get(criterion)
        if not isinstance(judgement, dict):
            raise TypeError(f"LLM Judge 응답에 {criterion} 판정이 없습니다.")
        score = judgement.get("score")
        reason = judgement.get("reason")
        if isinstance(score, bool) or not isinstance(score, int) or not 1 <= score <= 5:
            raise ValueError(f"{criterion} 점수는 1~5 정수여야 합니다.")
        if not isinstance(reason, str) or not reason.strip():
            raise ValueError(f"{criterion} 판정 근거가 비어 있습니다.")
        scores[criterion] = score
    return scores


def _evaluate_item(item: dict) -> dict:
    """한 문항의 모델 응답, 규칙 검사, Judge 점수와 내부 집계값을 만든다."""
    market_fixture = _sanitize_market_fixture(item)
    trend_fixture = _sanitize_trend_fixture(item)
    started_at = time.perf_counter()
    with (
        patch(
            "models.consult.nodes.market_for_consult.get_market",
            return_value=market_fixture,
        ),
        patch(
            "models.consult.nodes.trend_for_consult.get_trend",
            return_value=trend_fixture,
        ),
    ):
        try:
            final_state, response = _run_graph(_build_model_request(item))
        except Exception as exc:
            logger.exception("컨설턴트 평가 그래프 실행 실패")
            final_state = {}
            response = {
                "status": "error",
                "reason": classify_llm_error(exc),
                "message": "전략 생성 중 오류가 발생했습니다.",
            }
    latency_s = time.perf_counter() - started_at

    context_snapshot = final_state.get("context") or {}
    trend_path = check_trend_path(item, final_state) if final_state else None

    status_ok = response.get("status") == "ok"
    if not status_ok:
        return {
            "id": item["id"],
            "passed": False,
            "scores": {},
            "unexpected_numbers": [],
            "response": response,
            "context_snapshot": context_snapshot,
            "trend_path": trend_path,
            "judge_error": None,
            "_status_ok": False,
            "_contract_ok": False,
            "_judge_ok": None,
            "_latency_s": latency_s,
        }

    expected = item.get("expected") or {}
    contract_ok = _check_contract(response, expected)
    number_ok, unexpected_numbers = _check_number_rules(response, expected)
    try:
        scores = _judge_response(item, response, context_snapshot)
        judge_error = None
        judge_ok = True
    except (TypeError, ValueError, openai.OpenAIError) as exc:
        logger.exception("LLM Judge 평가 실패: %s", item["id"])
        scores = {}
        judge_error = (
            classify_llm_error(exc) if isinstance(exc, openai.OpenAIError) else "invalid_response"
        )
        judge_ok = False
    return {
        "id": item["id"],
        "passed": contract_ok and number_ok and judge_ok,
        "scores": scores,
        "unexpected_numbers": unexpected_numbers,
        "response": response,
        "context_snapshot": context_snapshot,
        "trend_path": trend_path,
        "judge_error": judge_error,
        "_status_ok": True,
        "_contract_ok": contract_ok,
        "_judge_ok": judge_ok,
        "_latency_s": latency_s,
    }


def _percentile(values: list[float], percentile: float) -> float:
    """외부 수치 라이브러리 없이 선형 보간 백분위수를 계산한다."""
    if not values:
        return 0.0
    ordered = sorted(values)
    position = (len(ordered) - 1) * percentile
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    weight = position - lower
    return ordered[lower] + (ordered[upper] - ordered[lower]) * weight


def _build_report(
    results: list[dict],
    *,
    area: str,
    fixture_version: str,
    trend_fixture_version: str,
    run_at: datetime,
    token_usage: dict[str, int | None],
) -> dict:
    """문항별 결과를 §10.4 발표용 집계 스키마로 변환한다."""
    item_count = len(results)
    scores = [score for result in results for score in result["scores"].values()]
    latencies = [result["_latency_s"] for result in results]
    judge_checks = [result["_judge_ok"] for result in results if result["_judge_ok"] is not None]

    def rate(count: int) -> float:
        return count / item_count if item_count else 0.0

    public_fields = (
        "id",
        "passed",
        "scores",
        "unexpected_numbers",
        "trend_path",
        "judge_error",
        "response",
        "context_snapshot",
    )
    return {
        "run_at": run_at.isoformat(),
        "area": area,
        "generation_model": OPENAI_MODEL,
        "judge_model": OPENAI_JUDGE_MODEL,
        "token_usage": token_usage,
        "dataset_version": DATASET_VERSION,
        "fixture_version": fixture_version,
        "trend_fixture_version": trend_fixture_version,
        "item_count": item_count,
        "metrics": {
            "llm_judge_avg": sum(scores) / len(scores) if scores else 0.0,
            "hallucination_rate": rate(
                sum(bool(result["unexpected_numbers"]) for result in results)
            ),
            "contract_compliance": rate(sum(result["_contract_ok"] for result in results)),
            "trend_path_match_rate": trend_path_match_rate(results),
            "judge_failure_rate": (
                sum(not judge_ok for judge_ok in judge_checks) / len(judge_checks)
                if judge_checks
                else 0.0
            ),
            "failure_rate": rate(sum(not result["_status_ok"] for result in results)),
            "latency_p50_s": _percentile(latencies, 0.50),
            "latency_p95_s": _percentile(latencies, 0.95),
        },
        "items": [{field: result[field] for field in public_fields} for result in results],
    }


def _fixture_version(items: list[dict]) -> str:
    """실행 대상 fixture의 첫 버전을 고르고 서로 다른 버전은 경고한다."""
    versions = []
    for item in items:
        fixture = (item.get("input") or {}).get("market_fixture") or {}
        version = fixture.get("fixture_version")
        if version and version not in versions:
            versions.append(version)
    if len(versions) > 1:
        logger.warning("서로 다른 fixture_version이 섞였습니다: %s", versions)
    return versions[0] if versions else "unknown"


def _trend_fixture_version(items: list[dict]) -> str:
    """실행 대상의 값 있는 트렌드 fixture 버전을 고르고 혼합 버전은 경고한다."""
    versions = []
    for item in items:
        fixture = (item.get("input") or {}).get("trend_fixture") or {}
        version = fixture.get("fixture_version")
        if version and version not in versions:
            versions.append(version)
    if len(versions) > 1:
        logger.warning("서로 다른 trend fixture_version이 섞였습니다: %s", versions)
    return versions[0] if versions else "unknown"


def evaluate_dataset(
    *,
    dataset_path: Path = DEFAULT_DATASET_PATH,
    area: str = "consult",
    limit: int | None = None,
    report_dir: Path = DEFAULT_REPORT_DIR,
) -> tuple[dict, Path]:
    """데이터셋을 직렬 평가하고 날짜별 §10.4 JSON 리포트를 저장한다."""
    if limit is not None and limit <= 0:
        raise ValueError("--limit은 양수여야 합니다.")

    dataset = json.loads(dataset_path.read_text(encoding="utf-8"))
    if not isinstance(dataset, list):
        raise TypeError("골든 데이터셋 최상위 값은 배열이어야 합니다.")
    area_items = [item for item in dataset if item.get("area") == area]
    if not area_items:
        raise ValueError(f"area={area!r}인 문항이 없습니다.")
    selected = area_items[:limit] if limit is not None else area_items

    run_at = datetime.now(ZoneInfo("Asia/Seoul"))
    total_tokens_before = shared_llm.get_total_tokens()
    generation_tokens_before = shared_llm.get_total_tokens(OPENAI_MODEL)
    judge_tokens_before = shared_llm.get_total_tokens(OPENAI_JUDGE_MODEL)
    results = []
    for index, item in enumerate(selected):
        results.append(_evaluate_item(item))
        if index < len(selected) - 1:
            time.sleep(SLEEP_SECONDS)

    processed_count = len(results)
    expected_count = min(limit, len(area_items)) if limit is not None else len(area_items)
    if processed_count != expected_count:
        raise RuntimeError(
            f"{area} 처리 건수 불일치: 기대 {expected_count}건, 실제 {processed_count}건"
        )
    print(f"{area} {len(area_items)}문항 중 {processed_count}건 처리")

    total_tokens = shared_llm.get_total_tokens() - total_tokens_before
    if OPENAI_MODEL == OPENAI_JUDGE_MODEL:
        generation_tokens = None
        judge_tokens = None
    else:
        generation_tokens = shared_llm.get_total_tokens(OPENAI_MODEL) - generation_tokens_before
        judge_tokens = shared_llm.get_total_tokens(OPENAI_JUDGE_MODEL) - judge_tokens_before

    report = _build_report(
        results,
        area=area,
        fixture_version=_fixture_version(selected),
        trend_fixture_version=_trend_fixture_version(selected),
        run_at=run_at,
        token_usage={
            "generation_tokens": generation_tokens,
            "judge_tokens": judge_tokens,
            "total_tokens": total_tokens,
        },
    )
    report_dir.mkdir(parents=True, exist_ok=True)
    scope = f"limit-{processed_count}" if limit is not None else "full"
    timestamp = run_at.strftime("%Y-%m-%d_%H%M%S_%f")
    report_path = report_dir / f"{timestamp}_{area}_{scope}.json"
    with report_path.open("x", encoding="utf-8") as report_file:
        json.dump(
            report,
            report_file,
            ensure_ascii=False,
            indent=2,
        )
    return report, report_path


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """평가 데이터셋, 대상 영역과 제한 또는 전체 실행 모드를 CLI에서 받는다."""
    parser = argparse.ArgumentParser(description="컨설턴트 골든 데이터셋 평가")
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET_PATH)
    parser.add_argument("--area", default="consult")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--limit", type=int)
    mode.add_argument("--full", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """CLI 평가를 실행하고 성공 여부를 종료 코드로 반환한다."""
    args = _parse_args(argv)
    if args.full:
        print("전체 측정 전 전민재 PM에게 사전 공유하고 팀 디스코드방의 !usage를 확인해야 합니다.")
    try:
        _, report_path = evaluate_dataset(
            dataset_path=args.dataset,
            area=args.area,
            limit=args.limit,
        )
    except Exception:
        logger.exception("컨설턴트 골든 데이터셋 평가 실패")
        return 1
    print(f"결과 파일: {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
