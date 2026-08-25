# models/consult/prompts/strategy.py 테스트 — 밀도 등급(density_tier)이 사용자 노출 답변에
# 그대로 인용되지 않는지 확인한다(D-044: 사용자 노출 reasons는 원시 수치만, 밀도 등급은
# 프롬프트 내부 힌트로만 사용).
import re

from models.consult.prompts.strategy import (
    FEWSHOT_NUMBERS,
    FEWSHOT_TERMS,
    RETRY_REASONS_HINT,
    SYSTEM_PROMPT,
    build_user_prompt,
)

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


def test_system_prompt_reasons_instruction_allows_trend_as_source() -> None:
    """reasons 허용 근거를 설명하는 문장(트렌드 전용 문단이 아니라 이 문장 자체)이
    "상권 데이터"만 언급하면, 트렌드만 있고 상권은 없는 요청에서 트렌드 근거를
    지어낸 것처럼 오인해 거부할 위험이 있다."""
    reasons_instruction = SYSTEM_PROMPT.split("예시:")[0].split("트렌드 데이터가 주어지면")[0]

    assert "트렌드" in reasons_instruction


def test_retry_hint_lists_trend_as_allowed_reasons_source() -> None:
    """재시도 힌트도 "상권 데이터"만 언급하면, 재생성 시 이미 프롬프트에 반영된 트렌드
    근거를 쓰지 말라는 상충 지시가 된다."""
    assert "트렌드" in RETRY_REASONS_HINT


def test_system_prompt_requests_title() -> None:
    """title은 backend/schemas.py의 ConsultantModelResult.title(min_length=1 필수)에
    대응한다 — 서비스가 Mock으로 대신 채워주고 있었을 뿐, 계약상 모델이 반환해야 한다
    (D7 계약 정합성 점검, PM 리뷰)."""
    assert '"title"' in SYSTEM_PROMPT


def test_system_prompt_examples_include_title() -> None:
    """few-shot 예시에도 title이 있어야 LLM이 실제로 그 위치·형식을 학습한다."""
    example_section = SYSTEM_PROMPT.split("예시:")[1]

    assert example_section.count('"title"') == 3


def test_fewshot_constants_match_actual_example_content() -> None:
    """FEWSHOT_NUMBERS/TERMS는 골든 문항 오염 검사(D-218)가 참조하는 상수다 — 실제
    SYSTEM_PROMPT 예시 구간에 등장하는 값과 어긋나면 검사 자체가 무의미해진다."""
    example_section = SYSTEM_PROMPT.split("예시:")[1]

    assert FEWSHOT_NUMBERS == [12, 20]
    for number in FEWSHOT_NUMBERS:
        assert str(number) in example_section

    assert FEWSHOT_TERMS == ["브런치 세트", "주말브런치", "브런치카페"]
    for term in FEWSHOT_TERMS:
        assert term in example_section


def test_build_user_prompt_includes_seasonality_section_when_given() -> None:
    store = {"name": "카페 코드잇", "type": "카페", "address": "서울 강남구 역삼동",
             "lat": 37.5, "lng": 127.0}
    seasonality = {
        "reference_date": "2026-08-24",
        "calendar_period": "8월 하순",
        "season_hint": "여름 말기",
    }

    prompt = build_user_prompt("질문", store, None, None, seasonality)

    assert "2026-08-24" in prompt
    assert "8월 하순" in prompt
    assert "여름 말기" in prompt


def test_build_user_prompt_omits_seasonality_section_when_none() -> None:
    """seasonality_for_consult 노드가 어떤 이유로든 아직 안 돈 상태(그래프 조기
    실행 등)에서도 상권·트렌드와 동일한 원칙으로 섹션 자체가 통째로 빠진다."""
    store = {"name": "카페 코드잇", "type": "카페", "address": "서울 강남구 역삼동",
             "lat": 37.5, "lng": 127.0}

    prompt = build_user_prompt("질문", store, None, None, None)

    assert "계절성" not in prompt


def test_system_prompt_allows_season_hint_in_summary_actions_not_reasons() -> None:
    normalized = " ".join(SYSTEM_PROMPT.split())
    assert "summary·actions에서" in normalized
    assert "reasons에는 이 판단 라벨을 그대로 근거로 쓰지 않는다" in normalized


def test_system_prompt_forbids_demand_claims_from_season_alone() -> None:
    """"여름 말기이므로 수요가 늘어난다"처럼 날짜만으로 실제 수요·검색량 증감을
    단정하면 안 되고, 검색 수요 증감은 트렌드 데이터가 실제로 주어졌을 때만
    주장해야 한다(PM 설계)."""
    normalized = " ".join(SYSTEM_PROMPT.split())
    assert "여름 말기이므로 수요가 늘어난다" in normalized
    assert "트렌드 데이터가 실제로 주어졌을 때만 주장한다" in normalized


def test_system_prompt_no_longer_claims_date_information_is_never_given() -> None:
    """계절성 참고가 실제로 날짜 정보를 주는 이상, "실제 날짜·계절 정보는 주어지지
    않으므로"라는 예전 문구가 남아있으면 자기모순이 된다(계절성 도입 전 트렌드
    규칙 — G-3의 "무료 증정 금지 직후 웰컴 선물" 자기모순과 같은 유형)."""
    assert "실제 날짜·계절 정보는 주어지지 않으므로" not in SYSTEM_PROMPT


def test_system_prompt_requires_explicit_zero_for_no_competitors() -> None:
    """동일 업종 매장 수가 0곳이면 reasons에도 "없다"가 아니라 반드시 "0곳"이라고
    숫자로 쓰라는 지시가 있어야 한다 — D8 60문항 실측에서 F1(경쟁 없음) fixture
    4건(C-009·C-032·C-049·C-050)이 전부 이 이유로 must_contain_number를
    못 채웠다."""
    normalized = " ".join(SYSTEM_PROMPT.split())
    assert '0곳이면 "경쟁이 없다"·"동일 업종이 없다"처럼 숫자 없이 쓰지 말고' in normalized
    assert 'reasons에도 반드시 "0곳"이라고 숫자로 명시한다' in normalized
