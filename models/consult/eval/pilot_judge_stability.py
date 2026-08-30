# 컨설턴트 응답을 고정해 Judge 점수 재현성을 확인하는 라이브 파일럿
"""컨설턴트 문항별 생성 1회와 동일 응답 Judge 3회 채점을 실행한다."""

import json
import logging
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from unittest.mock import patch
from zoneinfo import ZoneInfo

import openai

from models.consult.eval.eval_strategy import (
    DATASET_VERSION,
    DEFAULT_DATASET_PATH,
    _build_model_request,
    _item_reference_date,
    _judge_response,
    _run_graph,
    _sanitize_market_fixture,
    _sanitize_trend_fixture,
)
from models.shared.config import (
    LLM_JUDGE_TEMPERATURE,
    OPENAI_JUDGE_MODEL,
    OPENAI_MODEL,
)
from models.shared.eval.judge_stability import evaluate_stability
from models.shared.eval.token_usage import (
    build_token_usage,
    item_token_delta,
    preflight,
    token_snapshot,
)
from models.shared.llm_errors import classify_llm_error
from models.shared.seasonality import compute_seasonality

PILOT_ITEM_COUNT = 5
JUDGE_REPEAT = 3
DEFAULT_REPORT_DIR = Path(__file__).resolve().parent / "reports"

logger = logging.getLogger(__name__)

Generate = Callable[[dict], tuple[dict, dict]]
Judge = Callable[[dict, dict, dict], dict[str, int]]


def _load_pilot_items(dataset_path: Path) -> list[dict]:
    """데이터셋에서 앞쪽 컨설턴트 문항 5개를 읽는다."""
    dataset = json.loads(dataset_path.read_text(encoding="utf-8"))
    if not isinstance(dataset, list):
        raise TypeError("골든 데이터셋 최상위 값은 배열이어야 합니다.")
    items = [item for item in dataset if item.get("area") == "consult"][:PILOT_ITEM_COUNT]
    if len(items) != PILOT_ITEM_COUNT:
        raise ValueError(f"컨설턴트 안정성 파일럿에는 {PILOT_ITEM_COUNT}문항이 필요합니다.")
    return items


def _count_consult_items(dataset_path: Path) -> int:
    """안정성 외삽에 쓸 전체 컨설턴트 문항 수를 데이터셋에서 센다."""
    dataset = json.loads(dataset_path.read_text(encoding="utf-8"))
    if not isinstance(dataset, list):
        raise TypeError("골든 데이터셋 최상위 값은 배열이어야 합니다.")
    return sum(item.get("area") == "consult" for item in dataset)


def _generate_once(item: dict) -> tuple[dict, dict]:
    """fixture를 주입해 컨설턴트 그래프를 한 번 실행한다."""
    market_fixture = _sanitize_market_fixture(item)
    trend_fixture = _sanitize_trend_fixture(item)
    seasonality_fixture = compute_seasonality(_item_reference_date(item))
    with (
        patch(
            "models.consult.nodes.market_for_consult.get_market",
            return_value=market_fixture,
        ),
        patch(
            "models.consult.nodes.trend_for_consult.get_trend",
            return_value=trend_fixture,
        ),
        patch(
            "models.consult.nodes.seasonality_for_consult.compute_seasonality",
            return_value=seasonality_fixture,
        ),
    ):
        final_state, response = _run_graph(_build_model_request(item))
    if response.get("status") != "ok":
        raise RuntimeError(f"{item['id']} 생성 응답이 성공 상태가 아닙니다.")
    return response, final_state.get("context") or {}


def run_pilot(
    items: list[dict],
    *,
    generate: Generate = _generate_once,
    judge: Judge = _judge_response,
    target_item_count: int,
) -> dict:
    """응답을 문항당 한 번 생성하고 같은 입력을 세 번 채점한다."""
    for item in items:
        _item_reference_date(item)
    preflight()
    results = []
    failed_items = []
    runs_by_item: dict[str, dict[str, list[int]]] = {}

    for item in items:
        snapshot = token_snapshot()
        try:
            response, context = generate(item)
        except (ValueError, RuntimeError, openai.OpenAIError) as exc:
            logger.exception("컨설턴트 안정성 파일럿 생성 실패: %s", item["id"])
            generation_error = (
                classify_llm_error(exc)
                if isinstance(exc, openai.OpenAIError)
                else "invalid_response"
            )
            failed_items.append(item["id"])
            runs_by_item[item["id"]] = {}
            results.append(
                {
                    "id": item["id"],
                    "runs": [],
                    "spread": {},
                    "stable": False,
                    "generation_error": generation_error,
                    "tokens": item_token_delta(snapshot),
                }
            )
            break
        runs = [judge(item, response, context) for _ in range(JUDGE_REPEAT)]
        rubric = (item.get("expected") or {}).get("rubric") or {}
        spread = {
            criterion: max(run[criterion] for run in runs) - min(run[criterion] for run in runs)
            for criterion in rubric
        }
        runs_by_item[item["id"]] = {
            criterion: [run[criterion] for run in runs] for criterion in rubric
        }
        results.append(
            {
                "id": item["id"],
                "runs": runs,
                "spread": spread,
                "stable": False,
                "generation_error": None,
                "tokens": item_token_delta(snapshot),
            }
        )

    stability = evaluate_stability(runs_by_item, target_item_count)
    unstable_items = sorted(
        item_id
        for item_id in runs_by_item
        if any(detail.startswith(f"{item_id}·") for detail in stability["cells_over_1"])
        or any(
            detail.startswith(f"{item_id} ")
            for detail in stability["items_over_0_5"]
        )
    )
    for result in results:
        result["stable"] = bool(result["runs"]) and result["id"] not in unstable_items

    return {
        "dataset_version": DATASET_VERSION,
        "generation_model": OPENAI_MODEL,
        "judge_model": OPENAI_JUDGE_MODEL,
        "judge_temperature": LLM_JUDGE_TEMPERATURE,
        "judge_repeat": JUDGE_REPEAT,
        "item_count": len(items),
        "passed": stability["passed"] and not failed_items,
        "failed_items": failed_items,
        "unstable_items": unstable_items,
        "stability": stability,
        "token_usage": build_token_usage(),
        "items": results,
    }


def main(
    *,
    dataset_path: Path = DEFAULT_DATASET_PATH,
    report_dir: Path = DEFAULT_REPORT_DIR,
) -> int:
    """안정성 파일럿을 실행하고 고유한 JSON 리포트를 저장한다."""
    items = _load_pilot_items(dataset_path)
    target_item_count = _count_consult_items(dataset_path)
    report = run_pilot(items, target_item_count=target_item_count)
    report_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(ZoneInfo("Asia/Seoul")).strftime("%Y-%m-%d_%H%M%S_%f")
    report_path = report_dir / f"{timestamp}_consult_judge_stability.json"
    with report_path.open("x", encoding="utf-8") as report_file:
        json.dump(report, report_file, ensure_ascii=False, indent=2)

    failed = report["failed_items"] + report["unstable_items"]
    result = "통과" if report["passed"] else f"실패 {failed}"
    print(
        f"judge_model={report['judge_model']} "
        f"temperature={report['judge_temperature']} 재현성={result}"
    )
    print(
        f"generation_tokens={report['token_usage']['generation_tokens']} "
        f"judge_tokens={report['token_usage']['judge_tokens']}"
    )
    print(report_path)
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
