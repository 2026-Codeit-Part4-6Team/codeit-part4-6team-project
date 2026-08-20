# 컨설턴트 응답을 고정해 Judge 점수 재현성을 확인하는 라이브 파일럿
"""컨설턴트 문항별 생성 1회와 동일 응답 Judge 3회 채점을 실행한다."""

import json
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from unittest.mock import patch
from zoneinfo import ZoneInfo

from models.consult.eval.eval_strategy import (
    DEFAULT_DATASET_PATH,
    _build_model_request,
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
from models.shared.eval.token_usage import (
    build_token_usage,
    item_token_delta,
    preflight,
    token_snapshot,
)

PILOT_ITEM_COUNT = 5
JUDGE_REPEAT = 3
DEFAULT_REPORT_DIR = Path(__file__).resolve().parent / "reports"

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


def _generate_once(item: dict) -> tuple[dict, dict]:
    """fixture를 주입해 컨설턴트 그래프를 한 번 실행한다."""
    market_fixture = _sanitize_market_fixture(item)
    trend_fixture = _sanitize_trend_fixture(item)
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
        final_state, response = _run_graph(_build_model_request(item))
    if response.get("status") != "ok":
        raise RuntimeError(f"{item['id']} 생성 응답이 성공 상태가 아닙니다.")
    return response, final_state.get("context") or {}


def run_pilot(
    items: list[dict],
    *,
    generate: Generate = _generate_once,
    judge: Judge = _judge_response,
) -> dict:
    """응답을 문항당 한 번 생성하고 같은 입력을 세 번 채점한다."""
    preflight()
    results = []
    unstable_items = []

    for item in items:
        snapshot = token_snapshot()
        response, context = generate(item)
        runs = [judge(item, response, context) for _ in range(JUDGE_REPEAT)]
        rubric = (item.get("expected") or {}).get("rubric") or {}
        spread = {
            criterion: max(run[criterion] for run in runs) - min(run[criterion] for run in runs)
            for criterion in rubric
        }
        stable = all(value == 0 for value in spread.values())
        if not stable:
            unstable_items.append(item["id"])
        results.append(
            {
                "id": item["id"],
                "runs": runs,
                "spread": spread,
                "stable": stable,
                "tokens": item_token_delta(snapshot),
            }
        )

    return {
        "generation_model": OPENAI_MODEL,
        "judge_model": OPENAI_JUDGE_MODEL,
        "judge_temperature": LLM_JUDGE_TEMPERATURE,
        "judge_repeat": JUDGE_REPEAT,
        "item_count": len(items),
        "passed": not unstable_items,
        "unstable_items": unstable_items,
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
    report = run_pilot(items)
    report_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(ZoneInfo("Asia/Seoul")).strftime("%Y-%m-%d_%H%M%S_%f")
    report_path = report_dir / f"{timestamp}_consult_judge_stability.json"
    with report_path.open("x", encoding="utf-8") as report_file:
        json.dump(report, report_file, ensure_ascii=False, indent=2)

    result = "통과" if report["passed"] else f"실패 {report['unstable_items']}"
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
