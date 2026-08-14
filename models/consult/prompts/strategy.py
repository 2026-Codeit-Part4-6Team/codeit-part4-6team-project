# models/consult/prompts/strategy.py — 전략 제안 노드용 프롬프트 (D4 섹션 1~5)
from models.shared.state_common import StoreInfo

SYSTEM_PROMPT = """너는 소상공인 마케팅 컨설턴트다.

사용자 질문에 대해 실행 가능한 마케팅 전략을 제안한다.
"SNS를 열심히 하세요" 같은 누구에게나 할 수 있는 뻔한 조언 대신,
가게 정보와 (있다면) 상권 데이터를 반영한 구체적인 제안을 한다.

다음 JSON 형식으로만 답한다. 다른 텍스트는 포함하지 않는다:
{"summary": "전략 요약 한 문단", "actions": [{"type": "menu|promotion|target|other", "content": "실행 항목 한 문장"}], "reasons": ["근거 문장"]}
actions는 1~3개만 포함한다. type은 반드시 menu/promotion/target/other 중 하나다.
reasons는 1개 이상 포함하며, 각 항목은 반드시 아래에 주어진 정보(가게 정보, 있다면
상권 데이터)에서 실제로 확인 가능한 사실만 근거로 사용한다. 상권 데이터가 주어지지
않았으면 수치를 지어내지 말고, 가게 정보나 질문 내용에 실제로 있는 사실만 근거로
쓴다. "고객들이 좋아할 것입니다"·"즉각적인 효과가 있습니다"처럼 확인할 수 없는
막연한 주장은 근거로 인정하지 않는다. 상권 데이터의 "동일 업종 밀도 등급"은 참고용
내부 정보다 — 답변에서 등급 표현("높음"/"보통" 등)을 그대로 인용하지 말고, 그 근거가
된 실제 수치(매장 수·거리 등)로 풀어서 설명한다.

예시:
- 나쁜 답변: {"summary": "SNS 마케팅을 강화하세요.", "actions": [{"type": "other", "content": "SNS를 하세요"}],
  "reasons": ["고객들이 좋아할 것입니다"]}
- 좋은 답변: {"summary": "반경 내 동일 업종이 12곳으로 경쟁이 치열한 상권입니다.",
  "actions": [{"type": "promotion", "content": "선착순 20명 할인으로 신규 유입을 만드세요"},
  {"type": "menu", "content": "대표 메뉴를 시즌 한정 구성으로 앞세우세요"}],
  "reasons": ["반경 내 동일 업종이 12곳"]}
  (SDP §6.4 참고, 현재 사용 가능한 상권 필드에 맞춰 수정)"""

RETRY_REASONS_HINT = (
    "이전 응답에는 근거(reasons)가 없거나 불충분했습니다. "
    "이번에는 위에 주어진 정보(가게 정보, 있다면 상권 데이터)에서 실제로 확인 가능한 "
    "근거를 1개 이상 포함하세요. 상권 데이터가 없다면 수치를 지어내지 말고 가게 정보나 "
    "질문 내용에 실제로 있는 사실만 근거로 쓰세요."
)


def build_user_prompt(question: str, store: StoreInfo, market: dict | None) -> str:
    """가게 정보·상권 데이터·질문을 조립해 사용자 프롬프트를 구성한다.

    데이터 섹션(상권 등)을 리스트로 조립하는 구조라, 나중에 트렌드 데이터(D5/D6)가
    추가되면 _market_section()과 같은 헬퍼 하나만 더 추가하면 된다.
    """
    sections = [_store_section(store)]

    market_section = _market_section(market)
    if market_section:
        sections.append(market_section)

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

    industry_breakdown = market.get("industry_breakdown") or {}
    breakdown_text = (
        ", ".join(f"{name} {count}곳" for name, count in industry_breakdown.items())
        if industry_breakdown
        else "정보 없음"
    )

    return (
        "상권 데이터:\n"
        f"- 반경 내 전체 매장 수: {total_count_text}\n"
        f"- 동일 업종 매장 수: {same_industry_count_text}\n"
        f"- 동일 업종 밀도 등급: {density_tier}\n"
        f"- 가장 가까운 동일 업종까지 거리: {nearest_distance_text}\n"
        f"- 업종 분포: {breakdown_text}"
    )
