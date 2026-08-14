# models/consult/prompts/strategy.py 테스트 — 밀도 등급(density_tier)이 사용자 노출 답변에
# 그대로 인용되지 않는지 확인한다(D-044: 사용자 노출 reasons는 원시 수치만, 밀도 등급은
# 프롬프트 내부 힌트로만 사용).
import re

from models.consult.prompts.strategy import SYSTEM_PROMPT

_TIER_LABELS = ("높음", "보통", "낮음", "경쟁 없음", "판단 불가")


def test_system_prompt_example_does_not_leak_density_tier_labels() -> None:
    """"밀도 등급" 문구뿐 아니라 그 등급값 자체("높음" 등)도 예시에 없어야 한다 —
    문구만 막으면 "경쟁 수준은 높음"처럼 라벨만 바뀐 재발을 못 잡는다."""
    example_section = SYSTEM_PROMPT.split("예시:")[1]

    assert "밀도 등급" not in example_section
    for tier_label in _TIER_LABELS:
        assert tier_label not in example_section


def test_system_prompt_good_example_reasons_uses_raw_numbers() -> None:
    """D-044 핵심은 "사용자 노출 reasons"에 원시 수치를 쓰는 것이다 — summary에만
    숫자가 남고 reasons에서는 빠지는 회귀를 놓치지 않도록 reasons 부분만 따로
    검사한다(전체 예시 구간을 검사하면 이런 회귀를 통과시켜버린다)."""
    good_answer = SYSTEM_PROMPT.split("예시:")[1].split("좋은 답변:")[1]
    reasons_match = re.search(r'"reasons":\s*\[(.*?)\]', good_answer, re.DOTALL)

    assert reasons_match is not None
    assert re.search(r"\d+곳", reasons_match.group(1)) is not None
