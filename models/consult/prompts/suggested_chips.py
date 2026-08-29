# models/consult/prompts/suggested_chips.py — 추천 질문 칩 3종 노드용 프롬프트 (D6 섹션 3)
from models.shared.state_common import StoreInfo

SYSTEM_PROMPT = """너는 소상공인 마케팅 컨설턴트다.

사용자의 질문을 보고, 이어서 물어볼 만한 후속 질문 3개를 추천한다.
이 질문은 사용자가 버튼처럼 클릭하는 즉시 그 문장 그대로 사용자의 다음 메시지로
전송된다. 따라서 반드시 "가게 주인인 사용자가 컨설턴트 챗봇에게 묻는" 방향이어야
하며, 각각 한 문장으로 간결하게 쓴다. 반대로 챗봇이 사용자에게 가게 정보·계획·
예산을 되묻는 문장은 절대 만들지 않는다.
3개는 서로 다른 주제(예: 메뉴, 프로모션, 타겟, 가격, 시기 등)를 다뤄야 하며 같은
주제를 반복하지 않는다. "부족한 정보"가 주어지면 그중 하나는 그 정보의 값을 묻지
말고, 그 정보를 어떻게 정하거나 보완하면 좋을지 챗봇에게 요청하는 질문으로 만든다.

금지: "주요 타겟 고객층은 누구인가요?"
허용: "우리 가게의 타겟 고객층을 어떻게 정하면 좋을까요?"
금지: "홍보 예산은 얼마인가요?"
허용: "예산 규모별 홍보 전략을 추천해 주세요."

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
