# models/consult/prompts/strategy.py — 전략 제안 노드용 프롬프트 (D4 섹션 1~5)
from models.shared.state_common import StoreInfo

# few-shot 예시에 등장하는 키워드·수치 — 골든 문항과 겹치면 안 된다(D-218).
# 예시를 수정하면 이 목록도 함께 갱신한다.
FEWSHOT_TERMS = ["브런치 세트", "주말브런치", "브런치카페"]
FEWSHOT_NUMBERS = [12, 20]

SYSTEM_PROMPT = """너는 소상공인 마케팅 컨설턴트다.

사용자 질문에 대해 실행 가능한 마케팅 전략을 제안한다.
"SNS를 열심히 하세요" 같은 누구에게나 할 수 있는 뻔한 조언 대신,
가게 정보와 (있다면) 상권 데이터를 반영한 구체적인 제안을 한다.

다음 JSON 형식으로만 답한다. 다른 텍스트는 포함하지 않는다:
{"title": "전략 제목 한 문장", "summary": "전략 요약 한 문단", "actions": [{"type": "menu|promotion|target|other", "content": "실행 항목 한 문장"}], "reasons": ["근거 문장"]}
title은 이 전략을 한눈에 요약하는 짧은 제목이다(이력 목록에 노출되는 라벨).
actions는 1~3개만 포함한다. type은 반드시 menu/promotion/target/other 중 하나다.
reasons는 1개 이상 포함하며, 각 항목은 반드시 아래에 주어진 정보(가게 정보, 있다면
상권·트렌드 데이터)에서 실제로 확인 가능한 사실만 근거로 사용한다. 상권·트렌드
데이터가 주어지지 않았으면 수치를 지어내지 말고, 가게 정보나 질문 내용에 실제로
있는 사실만 근거로 쓴다. "고객들이 좋아할 것입니다"·"즉각적인 효과가 있습니다"처럼 확인할 수 없는
막연한 주장은 근거로 인정하지 않는다. 상권 데이터의 "동일 업종 밀도 등급"은 참고용
내부 정보다 — 답변에서 등급 표현("높음"/"보통" 등)을 그대로 인용하지 말고, 그 근거가
된 실제 수치(매장 수·거리 등)로 풀어서 설명한다.

트렌드 데이터가 주어지면 최근 검색 추이(상승/하락/유지)로 시의성을 반영한다 — 다만
실제 날짜·계절 정보는 주어지지 않으므로 "몇 월이라 좋다"처럼 구체적인 시기를 지어내지
말고, 추이 자체(예: 검색량이 늘고 있다)만 근거로 쓴다. 연관 검색어가 있다면 actions에
그 키워드를 활용한 구체적인 아이디어(메뉴명·프로모션 문구 등)로 반영한다.

예시:
- 나쁜 답변: {"title": "마케팅 전략", "summary": "SNS 마케팅을 강화하세요.", "actions": [{"type": "other", "content": "SNS를 하세요"}],
  "reasons": ["고객들이 좋아할 것입니다"]}
- 좋은 답변: {"title": "경쟁 상권 대응 프로모션", "summary": "반경 내 동일 업종이 12곳으로 경쟁이 치열한 상권입니다.",
  "actions": [{"type": "promotion", "content": "선착순 20명 할인으로 신규 유입을 만드세요"},
  {"type": "menu", "content": "대표 메뉴를 시즌 한정 구성으로 앞세우세요"}],
  "reasons": ["반경 내 동일 업종이 12곳"]}
  (SDP §6.4 참고, 현재 사용 가능한 상권 필드에 맞춰 수정)
- 좋은 답변(트렌드 반영): {"title": "브런치 세트 시의성 프로모션", "summary": "\'브런치 세트\' 검색량이 최근 상승 추세입니다. 지금 유입을 늘리기 좋은 시점입니다.",
  "actions": [{"type": "promotion", "content": "연관 검색어 \'주말브런치\'를 활용해 주말 한정 프로모션을 진행하세요"},
  {"type": "menu", "content": "연관 검색어 \'브런치카페\'에 맞춰 대표 메뉴 구성을 브런치 세트로 리브랜딩하세요"}],
  "reasons": ["\'브런치 세트\' 검색량이 최근 상승 추세"]}"""

RETRY_REASONS_HINT = (
    "이전 응답에는 근거(reasons)가 없거나 불충분했습니다. "
    "이번에는 위에 주어진 정보(가게 정보, 있다면 상권·트렌드 데이터)에서 실제로 확인 "
    "가능한 근거를 1개 이상 포함하세요. 상권·트렌드 데이터가 없다면 수치를 지어내지 "
    "말고 가게 정보나 질문 내용에 실제로 있는 사실만 근거로 쓰세요."
)

RETRY_ACTIONS_HINT = (
    "이전 응답에는 actions가 하나도 없었습니다. 이번에는 실행 가능한 항목을 1개 이상 포함하세요."
)


def build_user_prompt(question: str, store: StoreInfo, market: dict | None, trend: dict | None = None) -> str:
    """가게 정보·상권 데이터·트렌드 데이터·질문을 조립해 사용자 프롬프트를 구성한다.

    데이터 섹션(상권·트렌드)을 리스트로 조립하는 구조라, 나중에 데이터가 더 늘어나면
    _market_section()과 같은 헬퍼 하나만 더 추가하면 된다.
    """
    sections = [_store_section(store)]

    market_section = _market_section(market)
    if market_section:
        sections.append(market_section)

    trend_section = _trend_section(trend)
    if trend_section:
        sections.append(trend_section)

    sections.append(f'질문: "{question}"')
    return "\n\n".join(sections)


def _store_section(store: StoreInfo) -> str:
    return (
        "가게 정보:\n"
        f"- 이름: {store['name']}\n"
        f"- 업종: {store['type']}\n"
        f"- 주소: {store['address']}"
    )


def _market_section(market: dict | None) -> str:
    """상권 데이터가 없으면(조회 실패 등) 빈 문자열을 반환해 프롬프트에서 통째로 빠지게 한다."""
    if market is None:
        return ""

    total_count = market.get("total_count")
    total_count_text = f"{total_count}곳" if total_count is not None else "정보 없음"

    same_industry_count = market.get("same_industry_count")
    same_industry_count_text = f"{same_industry_count}곳" if same_industry_count is not None else "정보 없음"

    density_tier = market.get("density_tier") or "판단 불가"

    nearest_distance_m = market.get("nearest_distance_m")
    nearest_distance_text = f"{nearest_distance_m}m" if nearest_distance_m is not None else "해당 없음"

    # industry_breakdown은 넣지 않는다 — 원본 반경 내 매장이 API 페이지 상한(1000곳)을
    # 넘는 지역(예: 강남역 6,691곳)에서는 상위 일부만 반영된 부분집합이라, "업종 분포"로
    # 그대로 노출하면 부정확한 근거가 될 수 있다(PM 리뷰). same_industry_count는 별도
    # 업종코드 필터 호출(D-041/D-042)로 정확히 계산되므로 이 문제와 무관하다.
    return (
        "상권 데이터:\n"
        f"- 반경 내 전체 매장 수: {total_count_text}\n"
        f"- 동일 업종 매장 수: {same_industry_count_text}\n"
        f"- 동일 업종 밀도 등급: {density_tier}\n"
        f"- 가장 가까운 동일 업종까지 거리: {nearest_distance_text}"
    )


def _trend_section(trend: dict | None) -> str:
    """트렌드 데이터가 없으면(keyword 없음, 조회 실패 등) 빈 문자열을 반환해 프롬프트에서
    통째로 빠지게 한다(상권과 동일 원칙). weather는 아직 항상 None이라 포함하지 않는다."""
    if trend is None:
        return ""

    keyword = trend.get("keyword")
    keyword_text = keyword if isinstance(keyword, str) and keyword.strip() else "정보 없음"

    direction = trend.get("direction") or "판단 불가"

    related = trend.get("related") or []
    related_text = ", ".join(related) if related else "정보 없음"

    return (
        "트렌드 데이터:\n"
        f"- 조회 검색어: {keyword_text}\n"
        f"- 최근 검색 추이: {direction}\n"
        f"- 연관 검색어: {related_text}"
    )
