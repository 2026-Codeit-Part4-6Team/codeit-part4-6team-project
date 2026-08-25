"""골든 데이터셋 60문항이 실제 ModelRequest 검증을 통과하는지 확인한다."""
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from backend.schemas import ModelRequest
from models.shared.eval_fixtures import build_model_request

DATASET = Path("shared_data/golden_dataset.json")
REQUIRED_KEYS = {"id", "area", "type", "question", "input",
                 "expected", "author", "reviewed_by", "created_at"}


def load_dataset() -> list[dict]:
    return json.loads(DATASET.read_text(encoding="utf-8"))


@pytest.mark.skipif(not DATASET.exists(), reason="아직 데이터셋 파일이 없음")
def test_every_item_builds_a_valid_model_request():
    """모든 문항이 조립 후 ModelRequest 스키마를 통과해야 한다."""
    for item in load_dataset():
        try:
            ModelRequest.model_validate(build_model_request(item))
        except ValidationError as error:
            pytest.fail(f"{item['id']} 조립 실패: {error}")


@pytest.mark.skipif(not DATASET.exists(), reason="아직 데이터셋 파일이 없음")
def test_ids_are_unique_and_counts_match_spec():
    """id 중복이 없고 영역별 문항 수가 기준과 일치해야 한다."""
    items = load_dataset()
    ids = [i["id"] for i in items]
    assert len(ids) == len(set(ids)), "중복 id 존재"

    counts = {area: sum(1 for i in items if i["area"] == area)
              for area in ("basic", "consult", "refusal")}
    assert counts == {"basic": 25, "consult": 20, "refusal": 15}, counts


@pytest.mark.skipif(not DATASET.exists(), reason="아직 데이터셋 파일이 없음")
def test_required_keys_and_consult_fixture_present():
    """필수 키가 모두 있고, 컨설턴트 문항은 market_fixture 를 갖는다."""
    for item in load_dataset():
        assert REQUIRED_KEYS <= set(item), f"{item['id']} 필수 키 누락"
        if item["area"] == "consult":
            assert "market_fixture" in item["input"], \
                f"{item['id']} market_fixture 없음 — 실시간 API 의존은 금지(§4.4)"

@pytest.mark.skipif(not DATASET.exists(), reason="아직 데이터셋 파일이 없음")
def test_consult_items_declare_trend_fixture_and_expected_path():
    """trend_fixture 는 생략이 아니라 명시적 null 이어야 하고,
    trend_used 와 서로 모순되면 안 된다(§4.4)."""
    for item in load_dataset():
        if item["area"] != "consult":
            continue

        assert "trend_fixture" in item["input"], (
            f"{item['id']}: trend_fixture 키가 없다 — null 이라도 명시한다(§4.4)"
        )
        assert "trend_used" in item["expected"], (
            f"{item['id']}: expected.trend_used 누락 — 경로 검증이 불가능하다(§6.4)"
        )

        fixture = item["input"]["trend_fixture"]
        expected_used = item["expected"]["trend_used"]

        assert bool(fixture) == expected_used, (
            f"{item['id']}: trend_fixture 유무({bool(fixture)})와 "
            f"expected.trend_used({expected_used})가 어긋난다"
        )

        if fixture:
            assert fixture.get("fixture_version"), f"{item['id']}: fixture_version 누락"
            assert fixture.get("captured_at"), f"{item['id']}: captured_at 누락"
            assert fixture.get("weather") is None, (
                f"{item['id']}: weather 는 항상 null 이다 — "
                f"get_trend()가 값을 반환하지 않는다(D-230)"
            )
            assert "트렌드" in item["expected"]["must_include_sources"], (
                f"{item['id']}: trend_used=true 면 sources 에 '트렌드'가 있어야 한다"
            )
        else:
            assert "트렌드" not in item["expected"]["must_include_sources"], (
                f"{item['id']}: trend_used=false 인데 sources 에 '트렌드'를 기대하고 있다"
            )