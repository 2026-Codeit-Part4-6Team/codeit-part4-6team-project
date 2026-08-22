# models/consult/prompts/suggested_chips.py — 추천 질문 칩 3종 노드용 프롬프트 (D6 섹션 3)
from models.shared.state_common import StoreInfo

SYSTEM_PROMPT = """너는 소상공인 마케팅 컨설턴트다.

사용자의 질문을 보고, 이어서 물어볼 만한 후속 질문 3개를 추천한다.
사용자가 버튼처럼 클릭할 수 있는 짧은 질문이므로, 각각 한 문장으로 간결하게 쓴다.
3개는 서로 다른 주제(예: 메뉴, 프로모션, 타겟, 가격, 시기 등)를 다뤄야 하며 같은
주제를 반복하지 않는다. "부족한 정보"가 주어지면 그중 하나는 그 정보를 채우는
질문으로 만든다.

다음 JSON 형식으로만 답한다. 다른 텍스트는 포함하지 않는다:
{"chips": ["질문 1", "질문 2", "질문 3"]}
반드시 3개를 포함하며, 각 항목은 비어있지 않은 한 문장이어야 한다."""


def build_user_prompt(question: str, store: StoreInfo, missing_info: list[str]) -> str:
    """가게 정보·질문·(있으면) 부족한 정보를 조립해 사용자 프롬프트를 구성한다."""
    store_section = (
        "가게 정보:\n"
        f"- 이름: {store['name']}\n"
        f"- 업종: {store['type']}\n"
        f"- 주소: {store['address']}"
    )
    sections = [store_section, f'질문: "{question}"']

    if missing_info:
        sections.append("부족한 정보: " + ", ".join(missing_info))

    return "\n\n".join(sections)
