# models/consult/prompts/strategy.py 테스트 — 밀도 등급(density_tier)이 사용자 노출 답변에
# 그대로 인용되지 않는지 확인한다(D-044: 사용자 노출 reasons는 원시 수치만, 밀도 등급은
# 프롬프트 내부 힌트로만 사용).
import re

from models.consult.prompts.strategy import SYSTEM_PROMPT, build_user_prompt

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


def test_user_prompt_omits_industry_breakdown() -> None:
    """반경 내 원본 매장이 API 페이지 상한(1000곳)을 넘는 지역(예: 강남역 6,691곳)은
    industry_breakdown이 상위 일부만 반영된 부분집합이라, 그대로 프롬프트에 노출하면
    "업종 분포"라는 이름으로 부정확한 근거를 줄 수 있다(PM 리뷰). same_industry_count는
    별도 API 호출(D-041/D-042)로 정확하므로 영향이 없다 — industry_breakdown만 뺀다."""
    store = {"name": "카페 코드잇", "type": "카페", "address": "서울 강남구 역삼동",
             "lat": 37.5, "lng": 127.0}
    market = {
        "total_count": 6691,
        "same_industry_count": 177,
        "nearest_distance_m": 65,
        "density_tier": "높음",
        "industry_breakdown": {"한식": 39, "이용·미용": 33, "의원": 55},
    }

    prompt = build_user_prompt("질문", store, market)

    assert "업종 분포" not in prompt
    assert "한식" not in prompt
    # same_industry_count 등 나머지 상권 수치는 그대로 남아 있어야 한다.
    assert "177곳" in prompt
