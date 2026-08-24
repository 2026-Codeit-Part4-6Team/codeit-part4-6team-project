# 컨설턴트 업종 매핑 데이터 정확도를 측정하는 실행 스크립트
"""모델 출력이 아니라 입력 데이터(업종 코드 매핑) 자체의 정확도를 잰다(D-222).

기존 지표는 전부 LLM 응답 기준이라 "숫자가 있는가"만 볼 뿐 "그 숫자가 정확한
경로로 나왔는가"는 보지 못한다. industry_code_for()가 로컬 파일만 읽는 순수
함수라 LLM 호출도 실 API 호출도 없이(비용 무관) 골든 데이터셋만으로 계산한다.

업종 매핑이 되면 market_api.fetch_by_code()로 서버 사이드 필터 조회를 해
same_industry_count/nearest_distance_m을 정확히 계산하고(D-041/D-042), 안 되면
텍스트 매칭 폴백(최대 1000곳 캡·오탐 위험)으로 떨어진다 — 여기서 재는 값은
실제로 그래프를 돌려 확인한 결과가 아니라 코드 매핑 여부로 미리 판단한
"예상치"다. business_type이 자유 입력이고 운영 로그가 없어 이 결과를 "서비스
전체 커버리지"라고 부르면 안 되고, 항상 골든 데이터셋 범위로만 해석해야 한다.
"""

import argparse
import hashlib
import json
import logging
from collections import Counter
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from models.consult.clients.market_api import industry_code_for
from models.consult.eval.eval_strategy import DEFAULT_DATASET_PATH, DEFAULT_STORE

DATASET_VERSION = "v1.3"
DEFAULT_REPORT_DIR = Path(__file__).resolve().parent / "reports"

logger = logging.getLogger(__name__)


def _store_type(item: dict, *, default_store: dict = DEFAULT_STORE) -> str | None:
    """ModelRequest 조립 시(_build_model_request)와 동일한 폴백으로 업종 문자열을 뽑는다."""
    raw = item.get("input") or {}
    store = raw.get("store", default_store)
    return store.get("type")


def _collect_store_types(dataset: list[dict], *, area: str) -> list[str]:
    """대상 영역 문항의 업종 문자열 목록을 만든다(문항 수만큼, 중복 포함)."""
    types = []
    for item in dataset:
        if item.get("area") != area:
            continue
        store_type = _store_type(item)
        if store_type is not None:
            types.append(store_type)
    return types


def _measure_data_quality(store_types: list[str]) -> dict:
    """업종 매핑 커버리지·정확 판정 예상 비율을 계산한다."""
    unique_types = sorted(set(store_types))
    codes = {store_type: industry_code_for(store_type) for store_type in unique_types}
    mapped_types = [store_type for store_type in unique_types if codes[store_type] is not None]
    unmapped_types = [store_type for store_type in unique_types if codes[store_type] is None]

    items_total = len(store_types)
    items_with_code = sum(1 for store_type in store_types if codes[store_type] is not None)

    counts = Counter(store_types)
    industries = [
        {"type": store_type, "code": codes[store_type], "item_count": counts[store_type]}
        for store_type in unique_types
    ]

    return {
        "unique_industries": len(unique_types),
        "industries_with_code": len(mapped_types),
        "industry_mapping_coverage": (
            len(mapped_types) / len(unique_types) if unique_types else 0.0
        ),
        "items_total": items_total,
        "items_with_code": items_with_code,
        "accurate_determination_rate_estimated": (
            items_with_code / items_total if items_total else 0.0
        ),
        "unmapped_industries": unmapped_types,
        "industries": industries,
    }


def _source_dataset_provenance(dataset_path: Path) -> dict:
    """측정에 실제로 쓴 데이터셋 파일을 파일명·SHA-256으로 특정한다."""
    return {
        "file": dataset_path.name,
        "sha256": hashlib.sha256(dataset_path.read_bytes()).hexdigest(),
    }


def evaluate_data_quality(
    *,
    dataset_path: Path = DEFAULT_DATASET_PATH,
    area: str = "consult",
    report_dir: Path = DEFAULT_REPORT_DIR,
) -> tuple[dict, Path]:
    """골든 데이터셋 기준 업종 매핑 데이터 정확도를 측정하고 리포트를 저장한다."""
    dataset = json.loads(dataset_path.read_text(encoding="utf-8"))
    if not isinstance(dataset, list):
        raise TypeError("골든 데이터셋 최상위 값은 배열이어야 합니다.")

    store_types = _collect_store_types(dataset, area=area)
    if not store_types:
        raise ValueError(f"area={area!r}인 문항이 없습니다.")

    metrics = _measure_data_quality(store_types)
    run_at = datetime.now(ZoneInfo("Asia/Seoul"))

    report = {
        "run_at": run_at.isoformat(),
        "area": f"{area}_data_quality",
        # "서비스 전체 커버리지"가 아니라 골든 데이터셋 범위임을 리포트에도 명시한다
        # (business_type은 자유 입력이고 운영 로그가 없어 더 넓게 주장할 근거가 없다).
        "scope": f"golden_dataset:{area}",
        "dataset_version": DATASET_VERSION,
        "source_dataset": _source_dataset_provenance(dataset_path),
        "metrics": {
            key: value
            for key, value in metrics.items()
            if key not in ("unmapped_industries", "industries")
        },
        "unmapped_industries": metrics["unmapped_industries"],
        "industries": metrics["industries"],
    }

    report_dir.mkdir(parents=True, exist_ok=True)
    timestamp = run_at.strftime("%Y-%m-%d_%H%M%S_%f")
    report_path = report_dir / f"{timestamp}_{area}_data_quality.json"
    with report_path.open("x", encoding="utf-8") as report_file:
        json.dump(report, report_file, ensure_ascii=False, indent=2)
    return report, report_path


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """대상 영역을 CLI에서 받는다.

    --dataset을 임의로 받지 않는다 — golden_dataset.json 자체엔 버전 표시가
    없어서(순수 리스트), 다른 파일을 넣으면 결과에 찍히는 dataset_version이
    거짓이 된다(Codex 리뷰). --area도 consult 하나로 고정한다 — DEFAULT_STORE
    폴백과 industry_code_for()가 전부 컨설턴트 전용이라 다른 영역에 돌리면
    엉뚱한 커버리지가 나온다(Codex 리뷰).
    """
    parser = argparse.ArgumentParser(description="컨설턴트 업종 매핑 데이터 정확도 평가")
    parser.add_argument("--area", default="consult", choices=("consult",))
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """CLI 평가를 실행하고 성공 여부를 종료 코드로 반환한다."""
    args = _parse_args(argv)
    try:
        report, report_path = evaluate_data_quality(area=args.area)
    except Exception:
        logger.exception("데이터 정확도 평가 실패")
        return 1

    metrics = report["metrics"]
    print(f"측정 범위: golden_dataset {args.area} 문항")
    print(f"고유 업종: {metrics['unique_industries']}종")
    print(f"코드 매핑 성공: {metrics['industries_with_code']}종")
    print(f"업종 매핑 커버리지: {metrics['industry_mapping_coverage']:.0%}")
    print(f"정확 판정 예상 비율: {metrics['accurate_determination_rate_estimated']:.0%}")
    print(f"결과 파일: {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
