# 컨설턴트 suggested_chips 품질을 기존 평가 리포트 기반으로 채점하는 실행 스크립트
"""이미 실행된 골든 평가 리포트의 suggested_chips만 별도로 채점한다.

전략 본문 평가(eval_strategy.py)와 리포트를 분리한다 — 공용 §10.4 리포트
스키마를 건드리지 않고, 그래프를 다시 돌리지 않아 상권·트렌드·전략 LLM
호출을 중복하지 않는다. 리포트 items에는 question·store가 없으므로
골든 데이터셋과 id로 연결해서 채운다.
"""

import argparse
import hashlib
import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import openai

from models.consult.eval.eval_strategy import (
    DATASET_VERSION,
    DEFAULT_DATASET_PATH,
    DEFAULT_STORE,
)
from models.shared import llm as shared_llm
from models.shared.config import LLM_JUDGE_TEMPERATURE, OPENAI_JUDGE_MODEL, OPENAI_MODEL
from models.shared.eval.token_usage import EvalPreflightError, build_report_header, preflight
from models.shared.llm_errors import classify_llm_error

DEFAULT_REPORT_DIR = Path(__file__).resolve().parent / "reports"
SLEEP_SECONDS = 1.0
AREA = "consult_chips"
SOURCE_AREA = "consult"
_RUBRIC_CRITERIA = ("관련성", "비중복성", "다양성", "자연스러움", "화자방향")
# llm_judge_avg에 합산할 축 — 화자방향 추가 전 리포트와 측정 조건을 맞추기 위해
# 4축만 유지한다(Codex 리뷰: 5축을 그대로 합치면 이전 리포트와 llm_judge_avg를
# 전후 비교할 때 측정 조건이 달라져 왜곡된다). 화자방향은 speaker_direction_avg로
# 별도 집계한다.
_LLM_JUDGE_AVG_CRITERIA = ("관련성", "비중복성", "다양성", "자연스러움")

logger = logging.getLogger(__name__)

JUDGE_SYSTEM_PROMPT = """당신은 소상공인 컨설턴트 챗봇의 추천 질문(칩) 평가자입니다.
아래 rubric 5개 항목을 각각 1~5점으로 채점하고 판정 근거 한 문장을 작성하세요.
모든 항목은 5점이 가장 좋은 상태입니다.
반드시 다음 JSON 객체 형식으로만 답하세요.
{"평가항목": {"score": 1, "reason": "판정 근거 한 문장"}}

① 관련성 — 추천 질문 3개가 현재 질문·가게·전략과 관련이 있는가
1점: 질문·가게·전략과 전혀 무관한 일반적인 질문뿐임
2점: 업종 정도만 일치할 뿐 질문이나 전략 내용과는 연결되지 않음
3점: 세 질문 중 일부만 질문·가게·전략과 관련 있고 나머지는 일반적임
4점: 대부분의 질문이 질문·가게·전략 내용과 연결되나 한 개 정도는 다소 일반적임
5점: 세 질문 모두 질문·가게·전략 내용과 자연스럽게 이어짐

② 비중복성 — 세 질문이 서로 같은 의미를 반복하지 않는가
1점: 세 질문이 사실상 같은 내용을 표현만 바꿔 반복함
2점: 세 질문 중 두 개가 사실상 같은 주제를 다룸
3점: 주제는 다르지만 질문의 결이 비슷해 겹치는 인상을 줌
4점: 세 질문의 주제가 대체로 구분되나 미세하게 겹치는 부분이 있음
5점: 세 질문이 서로 겹치는 의미 없이 각자 다른 내용을 물음

③ 다양성 — 전략 실행, 고객 이해, 추가 데이터 확인 등 서로 다른 후속 축을 제공하는가
1점: 세 질문이 모두 같은 축(예: 전부 메뉴 관련)에 머무름
2점: 두 축만 오가며 세 번째 질문도 기존 두 축 중 하나를 반복함
3점: 세 축을 다루지만 그중 한 축은 억지로 끼워 맞춘 느낌임
4점: 세 질문이 서로 다른 축을 다루나 한 축이 다소 좁게 표현됨
5점: 세 질문이 서로 다른 축(전략 실행·고객 이해·추가 데이터 확인 등)을 각각 대표함

④ 자연스러움 — 소상공인이 바로 이어서 물을 수 있는 자연스러운 한국어 문장인가
1점: 번역투이거나 어색해 실제로 이어 묻기 어려움
2점: 의미는 통하지만 어색한 표현이나 반복이 자주 나타남
3점: 전반적으로 이해되지만 일부 문장이 부자연스러움
4점: 대부분 자연스러우나 한 문장 정도 다소 딱딱함
5점: 실제 대화에서 바로 이어 물을 수 있는 자연스러운 문장임

⑤ 화자방향 — 칩을 클릭하면 그 문장이 그대로 사용자의 다음 메시지로 전송된다.
세 질문 모두 "가게 주인인 사용자가 컨설턴트 챗봇에게 묻는" 방향인가(반대로 챗봇이
사용자에게 가게 정보·계획·예산을 되묻는 방향이면 안 됨). 어미(예: "-인가요?")만
보고 판단하지 말고 의미로 판단한다 — "타겟 고객층은 누구인가요?"(사용자 자신만
아는 정보를 되묻음, 역방향)와 "이 업종에 적합한 고객층은 누구인가요?"(챗봇의
일반 지식을 구함, 정방향)는 어미가 같아도 방향이 다르다.
1점: 세 질문 모두 챗봇이 사용자에게 가게의 현재 상태·계획·예산 등 본인만 아는 정보를 되묻는 방향임(예: "타겟 고객층은 누구인가요?")
2점: 세 질문 중 두 개가 챗봇→사용자 방향임
3점: 세 질문 중 한 개가 챗봇→사용자 방향이거나, 방향이 모호해 판단하기 어려움
4점: 세 질문 모두 사용자→챗봇 방향이나 그중 한 개는 다소 모호한 표현임
5점: 세 질문 모두 사용자가 챗봇에게 조언·정보를 요청하는 방향으로 명확함
"""


def _load_dataset_index(dataset: list[dict], *, area: str = SOURCE_AREA) -> dict[str, dict]:
    """골든 데이터셋(이미 로드된 리스트)을 id → {question, store} 색인으로 만든다."""
    index = {}
    for item in dataset:
        if item.get("area") != area:
            continue
        raw = item.get("input") or {}
        index[item["id"]] = {
            "question": item["question"],
            "store": raw.get("store", DEFAULT_STORE),
        }
    return index


def _load_chips_items(
    report: dict, dataset_index: dict[str, dict]
) -> tuple[list[dict], list[dict]]:
    """리포트 items를 데이터셋과 id로 연결해 채점 대상을 만든다.

    응답이 실패 상태이거나 데이터셋에서 id를 찾지 못하면 채점하지 않고
    제외 목록에 사유와 함께 남긴다 — 조용히 빠지면 item_count와 실제
    채점 건수가 왜 다른지 나중에 알 수 없다.
    """
    items = []
    excluded = []
    for result in report.get("items", []):
        item_id = result["id"]
        dataset_entry = dataset_index.get(item_id)
        if dataset_entry is None:
            excluded.append({"id": item_id, "reason": "dataset_id_not_found"})
            continue
        response = result.get("response") or {}
        if response.get("status") != "ok":
            excluded.append({"id": item_id, "reason": "source_response_not_ok"})
            continue
        strategy = response.get("strategy") or {}
        items.append(
            {
                "id": item_id,
                "question": dataset_entry["question"],
                "store": dataset_entry["store"],
                "chips": response.get("suggested_chips"),
                "strategy_summary": strategy.get("summary"),
                "strategy_actions": strategy.get("actions"),
            }
        )
    return items, excluded


def _check_chips_contract(chips: Any) -> bool:
    """정확히 3개의 비어있지 않은 문자열인지 확인한다(노드 계약과 동일 기준)."""
    if not isinstance(chips, list) or len(chips) != 3:
        return False
    return all(isinstance(chip, str) and chip.strip() for chip in chips)


def _has_exact_duplicate(chips: list[str]) -> bool:
    """정규화(양끝 공백 제거) 후 완전히 같은 문구가 있는지 확인한다."""
    normalized = [chip.strip() for chip in chips]
    return len(set(normalized)) < len(normalized)


def _judge_chips(item: dict) -> dict[str, int]:
    """rubric 5개 항목을 LLM Judge 한 번으로 채점하고 점수만 반환한다."""
    judge_input = {
        "question": item["question"],
        "store": item["store"],
        "strategy_summary": item["strategy_summary"],
        "strategy_actions": item["strategy_actions"],
        "chips": item["chips"],
    }
    raw, _ = shared_llm.call_llm(
        JUDGE_SYSTEM_PROMPT,
        json.dumps(judge_input, ensure_ascii=False),
        json_mode=True,
        model=OPENAI_JUDGE_MODEL,
        temperature=LLM_JUDGE_TEMPERATURE,
    )
    parsed = json.loads(raw)
    if not isinstance(parsed, dict):
        raise TypeError("LLM Judge 응답은 JSON 객체여야 합니다.")

    scores = {}
    for criterion in _RUBRIC_CRITERIA:
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
    """한 문항의 계약·중복 검사와(계약을 지켰을 때만) Judge 채점 결과를 만든다."""
    chips = item["chips"]
    contract_ok = _check_chips_contract(chips)

    if not contract_ok:
        return {
            "id": item["id"],
            "contract_ok": False,
            "exact_duplicate": None,
            "scores": {},
            "judge_error": None,
            "judge_skipped_reason": "contract_violation",
        }

    try:
        scores = _judge_chips(item)
        judge_error = None
    except (TypeError, ValueError, json.JSONDecodeError, openai.OpenAIError) as exc:
        logger.exception("suggested_chips LLM Judge 평가 실패: %s", item["id"])
        scores = {}
        judge_error = (
            classify_llm_error(exc) if isinstance(exc, openai.OpenAIError) else "invalid_response"
        )

    return {
        "id": item["id"],
        "contract_ok": True,
        "exact_duplicate": _has_exact_duplicate(chips),
        "scores": scores,
        "judge_error": judge_error,
        "judge_skipped_reason": None,
    }


def _axis_avg(results: list[dict], criterion: str) -> float | None:
    """채점된 문항 중 해당 축 점수만 모아 평균을 낸다.

    채점된 문항이 하나도 없으면 None을 반환한다 — 점수 범위는 1~5라서
    0.0은 "가장 낮은 점수"로 읽히지만 실제로는 측정 자체가 안 된 것이다.
    """
    values = [result["scores"][criterion] for result in results if criterion in result["scores"]]
    return sum(values) / len(values) if values else None


def _source_provenance(report_path: Path, report: dict) -> dict:
    """원본 리포트를 절대 경로 대신 파일명·run_at·SHA-256으로 특정한다."""
    return {
        "file": report_path.name,
        "run_at": report.get("run_at"),
        "sha256": hashlib.sha256(report_path.read_bytes()).hexdigest(),
    }


def _source_dataset_provenance(dataset_path: Path) -> dict:
    """id 연결에 실제로 쓴 데이터셋 파일을 파일명·SHA-256으로 특정한다.

    데이터셋 파일이 원본 리포트 생성 이후 바뀌었을 수 있다 — 그러면 지금
    id로 끌어온 question/store가 실제로 chips를 생성할 때 쓰인 입력과
    달라진다. 어느 데이터셋 파일을 썼는지 남겨야 그 가능성을 나중에
    추적할 수 있다.
    """
    return {
        "file": dataset_path.name,
        "sha256": hashlib.sha256(dataset_path.read_bytes()).hexdigest(),
    }


def _build_report(
    results: list[dict],
    *,
    excluded: list[dict],
    source_provenance: dict,
    source_dataset: dict,
    source_header: dict,
    run_at: datetime,
) -> dict:
    """채점 결과를 chips 전용 리포트 스키마로 조립한다."""
    item_count = len(results)
    judged = [result for result in results if result["contract_ok"]]
    scored = [result for result in judged if result["scores"]]
    all_scores = [
        score
        for result in scored
        for criterion, score in result["scores"].items()
        if criterion in _LLM_JUDGE_AVG_CRITERIA
    ]

    def rate(count: int, denominator: int) -> float:
        return count / denominator if denominator else 0.0

    header = build_report_header(
        area=AREA,
        dataset_version=source_header.get("dataset_version", DATASET_VERSION),
        fixture_version=source_header.get("fixture_version", "unknown"),
        trend_fixture_version=source_header.get("trend_fixture_version", "unknown"),
        item_count=item_count,
    )
    # 채점 대상 chips는 오늘이 아니라 source_report 시점에 생성됐다 — 현재
    # .env 값을 그대로 쓰면 실제로 무엇을 채점했는지가 리포트에서 사라진다
    # (evaluate_chips가 이미 현재 env와 다르면 실행 전에 막는다).
    header["generation_model"] = source_header.get("generation_model", header["generation_model"])
    header["generation_temperature"] = source_header.get(
        "generation_temperature", header["generation_temperature"]
    )
    header["run_at"] = run_at.isoformat()

    return {
        **header,
        "source_report": source_provenance,
        "source_dataset": source_dataset,
        "metrics": {
            "contract_compliance": rate(len(judged), item_count),
            "exact_duplicate_rate": rate(
                sum(bool(result["exact_duplicate"]) for result in judged), len(judged)
            ),
            "relevance_avg": _axis_avg(scored, "관련성"),
            "non_redundancy_avg": _axis_avg(scored, "비중복성"),
            "diversity_avg": _axis_avg(scored, "다양성"),
            "naturalness_avg": _axis_avg(scored, "자연스러움"),
            "speaker_direction_avg": _axis_avg(scored, "화자방향"),
            "llm_judge_avg": sum(all_scores) / len(all_scores) if all_scores else None,
            "judge_failure_rate": rate(sum(not result["scores"] for result in judged), len(judged)),
            "excluded_count": len(excluded),
        },
        "excluded": excluded,
        "items": results,
    }


def evaluate_chips(
    *,
    report_path: Path,
    dataset_path: Path = DEFAULT_DATASET_PATH,
    limit: int | None = None,
    report_dir: Path = DEFAULT_REPORT_DIR,
) -> tuple[dict, Path]:
    """리포트 JSON의 suggested_chips만 데이터셋과 연결해 별도로 채점한다."""
    if limit is not None and limit <= 0:
        raise ValueError("--limit은 양수여야 합니다.")

    source_report = json.loads(report_path.read_text(encoding="utf-8"))
    source_generation_model = source_report.get("generation_model")
    if source_generation_model != OPENAI_MODEL:
        raise EvalPreflightError(
            f"현재 환경 OPENAI_MODEL='{OPENAI_MODEL}'이 리포트의 "
            f"generation_model='{source_generation_model}'과 다릅니다. "
            ".env를 리포트 생성 당시 모델로 맞추거나 올바른 리포트를 지정하세요."
        )

    dataset = json.loads(dataset_path.read_text(encoding="utf-8"))
    if not isinstance(dataset, list):
        raise TypeError("골든 데이터셋 최상위 값은 배열이어야 합니다.")
    dataset_index = _load_dataset_index(dataset)
    items, excluded = _load_chips_items(source_report, dataset_index)
    selected = items[:limit] if limit is not None else items

    preflight()
    run_at = datetime.now(ZoneInfo("Asia/Seoul"))
    results = []
    for index, item in enumerate(selected):
        results.append(_evaluate_item(item))
        if index < len(selected) - 1:
            time.sleep(SLEEP_SECONDS)

    processed_count = len(results)
    expected_count = min(limit, len(items)) if limit is not None else len(items)
    if processed_count != expected_count:
        raise RuntimeError(
            f"chips 처리 건수 불일치: 기대 {expected_count}건, 실제 {processed_count}건"
        )
    print(f"chips {len(items)}문항 중 {processed_count}건 처리(제외 {len(excluded)}건)")

    report = _build_report(
        results,
        excluded=excluded,
        source_provenance=_source_provenance(report_path, source_report),
        source_dataset=_source_dataset_provenance(dataset_path),
        source_header=source_report,
        run_at=run_at,
    )
    report_dir.mkdir(parents=True, exist_ok=True)
    scope = f"limit-{processed_count}" if limit is not None else "full"
    timestamp = run_at.strftime("%Y-%m-%d_%H%M%S_%f")
    report_path_out = report_dir / f"{timestamp}_{AREA}_{scope}.json"
    with report_path_out.open("x", encoding="utf-8") as report_file:
        json.dump(report, report_file, ensure_ascii=False, indent=2)
    return report, report_path_out


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """평가할 원본 리포트, 데이터셋, 대상 범위를 CLI에서 받는다."""
    parser = argparse.ArgumentParser(description="컨설턴트 suggested_chips 품질 평가")
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET_PATH)
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
        _, report_path = evaluate_chips(
            report_path=args.report,
            dataset_path=args.dataset,
            limit=args.limit,
        )
    except Exception:
        logger.exception("suggested_chips 평가 실패")
        return 1
    print(f"결과 파일: {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
