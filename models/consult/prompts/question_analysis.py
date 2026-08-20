# models/consult/prompts/question_analysis.py — 질문 분석 노드용 프롬프트
from models.shared.state_common import StoreInfo

SYSTEM_PROMPT = """너는 소상공인 마케팅 컨설턴트 챗봇의 질문 전처리 담당이다.

사용자 질문에 "여기", "우리 가게"처럼 대명사나 생략된 맥락이 있으면 아래 제공되는
가게 정보를 이용해 명확한 질문으로 재작성한다. 그리고 이 질문에 상권 분석이나
마케팅 전략을 제안하기에 정보가 충분한지 판단한다.

반드시 아래 JSON 형식으로만 답하라. 다른 설명은 절대 추가하지 마라.
{
  "rewritten_question": "재작성된 질문 문자열",
  "is_sufficient": true 또는 false,
  "missing_info": ["부족한 정보 항목", ...],
  "keyword": "트렌드 조회용 검색어 또는 null"
}

정보가 충분하면 missing_info는 빈 배열로 둔다.
keyword는 질문에 특정 메뉴·상품·이슈가 명시돼 있으면 그 단어 하나만 뽑는다
(예: "아이스아메리카노 요즘 잘 나갈까요?" → "아이스아메리카노"). 그런 구체적인
대상이 없으면(예: "우리 가게 마케팅 어떻게 하죠?") null로 둔다."""


def build_user_prompt(question: str, store: StoreInfo) -> str:
    """가게 정보와 사용자 질문을 하나의 사용자 프롬프트 문자열로 구성한다."""
    return (
        "가게 정보:\n"
        f"- 이름: {store['name']}\n"
        f"- 업종: {store['type']}\n"
        f"- 주소: {store['address']}\n\n"
        f'사용자 질문: "{question}"'
    )
