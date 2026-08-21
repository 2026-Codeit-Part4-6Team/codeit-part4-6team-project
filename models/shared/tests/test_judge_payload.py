"""models/shared/tests/test_judge_payload.py — Judge 프롬프트 페이로드 정제 (D-329~D-331)"""
import base64
import json
import os

import pytest

from models.shared.eval.judge_payload import (
    DROP_FIELDS,
    JudgePayloadTooLarge,
    dumps_for_judge,
    strip_for_report,
)


def _b64(kb: int) -> str:
    return base64.b64encode(os.urandom(kb * 1024)).decode()


def basic_response(image_kb: int = 1500) -> dict:
    return {
        "status": "ok", "title": "여름 신메뉴",
        "proposals": [{"copy": f"문구 {i}", "image_b64": _b64(image_kb), "error": None}
                      for i in range(3)],
        "sources": ["상권분석", "트렌드"], "tokens_used": 1520, "suggested_chips": [],
    }


def test_image_never_reaches_the_judge_prompt():
    """★ 이 파일의 존재 이유 — base64 이미지는 프롬프트에 들어가면 안 된다."""
    text, dropped = dumps_for_judge(basic_response())
    assert "image_b64" not in text
    assert len(dropped) == 3
    assert len(text) < 1_000, f"정제 후 {len(text):,}자 — 이미지가 남아 있다"


def test_copies_survive_the_cleaning():
    """채점 대상인 카피는 그대로 남아야 한다."""
    text, _ = dumps_for_judge(basic_response())
    for i in range(3):
        assert f"문구 {i}" in text


def test_consultant_response_is_untouched():
    """컨설턴트 응답에는 이미지 필드가 없어 영향이 없다."""
    payload = {"status": "ok", "title": "여름 전략",
               "strategy": {"summary": "s", "actions": [{"type": "target", "content": "c"}]},
               "reasons": ["r"], "sources": ["상권분석"], "tokens_used": 2400,
               "suggested_chips": ["a", "b", "c"]}
    text, dropped = dumps_for_judge(payload)
    assert dropped == []
    assert json.loads(text) == payload


@pytest.mark.parametrize("field", sorted(DROP_FIELDS))
def test_every_declared_drop_field_is_removed(field):
    text, dropped = dumps_for_judge({"status": "ok", "proposals": [{"copy": "a", field: "x" * 100}]})
    assert field not in text
    assert dropped


def test_unknown_large_field_raises_instead_of_being_truncated():
    """DROP_FIELDS 에 없는 새 대형 필드는 자르지 않고 멈춘다(D-330).

    잘라서 채점하면 '무엇을 채점했는지' 가 달라져 재현성이 깨진다(§1.4).
    """
    with pytest.raises(JudgePayloadTooLarge, match="debug_dump"):
        dumps_for_judge({"status": "ok", "proposals": [{"copy": "a"}], "debug_dump": "x" * 30_000})


def test_abnormally_long_copy_also_raises():
    """카피 자체가 비정상적으로 길어도 멈춘다 — 생성 노드 이상 신호다."""
    with pytest.raises(JudgePayloadTooLarge, match="copy"):
        dumps_for_judge({"status": "ok", "proposals": [{"copy": "y" * 5_000}]})


def test_report_keeps_copy_but_drops_image():
    """결과 파일은 이미지만 빼고 원본을 보존한다(D-331 · DoD ③)."""
    kept, dropped = strip_for_report(basic_response())
    serialized = json.dumps(kept, ensure_ascii=False)
    assert "image_b64" not in serialized
    assert len(dropped) == 3
    assert [p["copy"] for p in kept["proposals"]] == ["문구 0", "문구 1", "문구 2"]
    assert len(serialized) < 1_000


def test_report_does_not_raise_on_long_text():
    """리포트 보존은 상한 검사를 하지 않는다 — 기록이 목적이라 멈추면 안 된다."""
    kept, _ = strip_for_report({"status": "ok", "proposals": [{"copy": "y" * 5_000}]})
    assert len(kept["proposals"][0]["copy"]) == 5_000


def test_empty_and_none_are_safe():
    assert dumps_for_judge({})[0] == "{}"
    assert strip_for_report(None)[0] == {}
