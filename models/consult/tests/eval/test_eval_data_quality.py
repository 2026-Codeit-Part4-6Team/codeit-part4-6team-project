# 컨설턴트 데이터 정확도(업종 매핑 커버리지) 평가기 테스트
import json

import pytest

from models.consult.eval.eval_data_quality import (
    DEFAULT_STORE,
    _collect_store_types,
    _measure_data_quality,
    _parse_args,
    _source_dataset_provenance,
    _store_type,
    evaluate_data_quality,
)


def _item(*, item_id: str = "C-001", area: str = "consult", store_type: str | None = "카페") -> dict:
    item = {"id": item_id, "area": area, "question": "q"}
    if store_type is not None:
        item["input"] = {"store": {"name": "가게", "type": store_type}}
    else:
        item["input"] = {}
    return item


def test_store_type_uses_explicit_store() -> None:
    assert _store_type(_item(store_type="치킨")) == "치킨"


def test_store_type_falls_back_to_default_store() -> None:
    assert _store_type(_item(store_type=None)) == DEFAULT_STORE["type"]


def test_collect_store_types_filters_by_area() -> None:
    dataset = [
        _item(item_id="C-001", area="consult", store_type="카페"),
        _item(item_id="B-001", area="basic", store_type="치킨"),
        _item(item_id="C-002", area="consult", store_type=None),
    ]

    types = _collect_store_types(dataset, area="consult")

    assert types == ["카페", DEFAULT_STORE["type"]]


def test_measure_data_quality_computes_coverage_and_accuracy() -> None:
    store_types = ["카페", "카페", "치킨", "미용실", "슈퍼마켓"]

    metrics = _measure_data_quality(store_types)

    assert metrics["unique_industries"] == 4
    assert metrics["industries_with_code"] == 4
    assert metrics["industry_mapping_coverage"] == pytest.approx(1.0)
    assert metrics["items_total"] == 5
    assert metrics["items_with_code"] == 5
    assert metrics["accurate_determination_rate_estimated"] == pytest.approx(1.0)
    assert metrics["unmapped_industries"] == []
    industries_by_type = {row["type"]: row for row in metrics["industries"]}
    assert industries_by_type["카페"]["item_count"] == 2
    assert industries_by_type["카페"]["code"] is not None


def test_measure_data_quality_reports_unmapped_industries() -> None:
    store_types = ["카페", "존재하지않는업종"]

    metrics = _measure_data_quality(store_types)

    assert metrics["unique_industries"] == 2
    assert metrics["industries_with_code"] == 1
    assert metrics["industry_mapping_coverage"] == pytest.approx(0.5)
    assert metrics["items_with_code"] == 1
    assert metrics["accurate_determination_rate_estimated"] == pytest.approx(0.5)
    assert metrics["unmapped_industries"] == ["존재하지않는업종"]


def test_measure_data_quality_empty_list_does_not_crash() -> None:
    metrics = _measure_data_quality([])

    assert metrics["unique_industries"] == 0
    assert metrics["industry_mapping_coverage"] == 0.0
    assert metrics["items_total"] == 0
    assert metrics["accurate_determination_rate_estimated"] == 0.0


def test_source_dataset_provenance_hashes_actual_file_bytes(tmp_path) -> None:
    dataset_path = tmp_path / "golden_dataset.json"
    dataset_path.write_text(json.dumps([_item()]), encoding="utf-8")

    provenance = _source_dataset_provenance(dataset_path)

    assert provenance["file"] == "golden_dataset.json"
    assert len(provenance["sha256"]) == 64


def test_evaluate_data_quality_builds_report_and_writes_file(tmp_path) -> None:
    dataset_path = tmp_path / "golden_dataset.json"
    dataset_path.write_text(
        json.dumps(
            [
                _item(item_id="C-001", store_type="카페"),
                _item(item_id="C-002", store_type="치킨"),
                _item(item_id="B-001", area="basic", store_type="치킨"),
            ]
        ),
        encoding="utf-8",
    )
    report_dir = tmp_path / "reports"

    report, report_path = evaluate_data_quality(
        dataset_path=dataset_path, area="consult", report_dir=report_dir
    )

    assert report_path.exists()
    assert report["area"] == "consult_data_quality"
    assert report["scope"] == "golden_dataset:consult"
    assert report["source_dataset"]["file"] == "golden_dataset.json"
    assert report["metrics"]["unique_industries"] == 2
    assert report["metrics"]["items_total"] == 2
    saved = json.loads(report_path.read_text(encoding="utf-8"))
    assert saved == report


def test_evaluate_data_quality_raises_for_non_list_dataset(tmp_path) -> None:
    dataset_path = tmp_path / "golden_dataset.json"
    dataset_path.write_text(json.dumps({"not": "a list"}), encoding="utf-8")

    with pytest.raises(TypeError):
        evaluate_data_quality(dataset_path=dataset_path, report_dir=tmp_path / "reports")


def test_evaluate_data_quality_raises_when_area_has_no_items(tmp_path) -> None:
    dataset_path = tmp_path / "golden_dataset.json"
    dataset_path.write_text(json.dumps([_item(area="basic")]), encoding="utf-8")

    with pytest.raises(ValueError):
        evaluate_data_quality(
            dataset_path=dataset_path, area="consult", report_dir=tmp_path / "reports"
        )


def test_parse_args_defaults() -> None:
    args = _parse_args([])

    assert args.area == "consult"
    assert args.dataset is not None
