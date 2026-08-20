"""models/shared/tests/test_token_usage.py — 평가 산출물 헤더·토큰 블록 검증 (D-278)"""
from unittest.mock import MagicMock, patch

import pytest

import models.shared.llm as L
from models.shared.eval import token_usage as T


def _r(tok):
    r = MagicMock(); r.choices=[MagicMock(message=MagicMock(content="ok"))]
    r.usage = MagicMock(total_tokens=tok); return r

def test_preflight_blocks_when_models_identical(monkeypatch):
    monkeypatch.setattr(T, "OPENAI_JUDGE_MODEL", "gpt-4o-mini")
    monkeypatch.setattr(T, "OPENAI_MODEL", "gpt-4o-mini")
    with pytest.raises(T.EvalPreflightError) as e:
        T.preflight()
    assert "OPENAI_JUDGE_MODEL" in str(e.value)
    print("  ✅ 두 모델명이 같으면 평가 시작 자체를 막는다")

@patch("models.shared.llm.OpenAI")
def test_by_model_is_source_of_truth(mock_cls, monkeypatch):
    monkeypatch.setattr(T, "OPENAI_MODEL", "gen-m"); monkeypatch.setattr(T, "OPENAI_JUDGE_MODEL", "judge-m")
    c = MagicMock(); c.chat.completions.create.side_effect=[_r(12000), _r(4000), _r(500)]
    mock_cls.return_value = c
    L.reset_client(); L.reset_total_tokens()
    L.call_llm("s","u", model="gen-m")
    L.call_llm("s","u", model="judge-m", temperature=0.0)
    L.call_llm("s","u", model="몰래-끼어든-모델")     # 계획에 없던 호출
    u = T.build_token_usage()
    assert u["by_model"] == {"gen-m":12000, "judge-m":4000}
    assert u["generation_tokens"]==12000 and u["judge_tokens"]==4000
    assert u["total_tokens"]==16500
    assert u["unattributed_tokens"]==500
    print(f"  ✅ 미귀속 토큰 {u['unattributed_tokens']} 이 드러난다 (팀원 제안 구조였다면 은폐됨)")

@patch("models.shared.llm.OpenAI")
def test_refusal_area_must_not_call_judge(mock_cls, monkeypatch):
    monkeypatch.setattr(T, "OPENAI_MODEL", "gen-m"); monkeypatch.setattr(T, "OPENAI_JUDGE_MODEL", "judge-m")
    c = MagicMock(); c.chat.completions.create.return_value=_r(4000); mock_cls.return_value=c
    L.reset_client(); L.reset_total_tokens()
    L.call_llm("s","u", model="judge-m")
    with pytest.raises(T.EvalPreflightError):
        T.assert_no_judge_calls({"token_usage": T.build_token_usage()})
    print("  ✅ R- 영역에서 Judge 가 돌면 실패 처리된다")

@patch("models.shared.llm.OpenAI")
def test_item_level_delta(mock_cls, monkeypatch):
    monkeypatch.setattr(T, "OPENAI_MODEL","gen-m"); monkeypatch.setattr(T,"OPENAI_JUDGE_MODEL","judge-m")
    c=MagicMock(); c.chat.completions.create.side_effect=[_r(100),_r(40),_r(300),_r(60)]; mock_cls.return_value=c
    L.reset_client(); L.reset_total_tokens()
    s=T.token_snapshot(); L.call_llm("s","u",model="gen-m"); L.call_llm("s","u",model="judge-m")
    d1=T.item_token_delta(s)
    s=T.token_snapshot(); L.call_llm("s","u",model="gen-m"); L.call_llm("s","u",model="judge-m")
    d2=T.item_token_delta(s)
    assert d1=={"generation":100,"judge":40} and d2=={"generation":300,"judge":60}
    print("  ✅ 문항별 토큰이 분리 기록된다 (어느 문항이 비쌌는지 추적 가능)")
