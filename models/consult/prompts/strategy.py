# models/consult/prompts/strategy.py — 전략 제안 노드용 프롬프트 (D4 섹션 1: 질문만으로 생성)
from models.shared.state_common import StoreInfo

SYSTEM_PROMPT = """너는 소상공인 마케팅 컨설턴트다.

사용자 질문에 대해 실행 가능한 마케팅 전략을 한 문단으로 제안한다.
"SNS를 열심히 하세요" 같은 누구에게나 할 수 있는 뻔한 조언 대신,
가게 정보를 반영한 구체적인 제안을 한다."""


def build_user_prompt(question: str, store: StoreInfo) -> str:
    """가게 정보와 사용자 질문을 하나의 사용자 프롬프트 문자열로 구성한다."""
    return (
        "가게 정보:\n"
        f"- 이름: {store['name']}\n"
        f"- 업종: {store['type']}\n"
        f"- 주소: {store['address']}\n\n"
        f'질문: "{question}"'
    )
