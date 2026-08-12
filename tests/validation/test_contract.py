"""
tests/test_contract.py.py

* VSCode - uv 터미널 실행 명령어(test_contract.py.py)
uv run pytest tests/validation/test_contract.py.py -q
"""

"""검증 함수 4종 계약 스모크 테스트 — 스텁이든 실구현이든 항상 통과해야 함"""
from validation.security import check_input, check_output
from validation.regulation import check_regulation
from validation.self_check import self_check


def test_check_input():
    r = check_input("테스트 질문")
    assert r["action"] in ("pass", "warn", "block")
    assert isinstance(r["message"], str)


def test_check_output():
    r = check_output("테스트 답변")
    assert r["action"] in ("pass", "warn", "block")


def test_check_regulation():
    r = check_regulation("우리 가게가 최고입니다")
    assert r["action"] in ("pass", "warn", "block")
    for k in ("law", "reason", "alternative", "message"):
        assert isinstance(r[k], str), f"{k} 는 문자열이어야 함"


def test_self_check():
    r = self_check({"proposals": []}, {})
    assert r["action"] in ("pass", "warn", "reject")
    assert isinstance(r["reasons"], list)