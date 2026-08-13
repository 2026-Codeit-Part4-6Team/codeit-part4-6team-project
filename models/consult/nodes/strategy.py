# 마케팅 전략 제안 노드 (가장 중요) — D4 섹션 1: 질문만으로 전략 하나 생성
from models.consult.graph.state import ConsultState
from models.consult.llm import call_llm
from models.consult.prompts.strategy import SYSTEM_PROMPT, build_user_prompt


def strategy(state: ConsultState) -> dict:
    """질문(+가게 정보)만으로 전략 요약을 생성한다.

    아직 상권·트렌드 데이터 연동(D4 섹션 2), actions 구조화(섹션 3),
    근거 필수화(섹션 4)는 하지 않는다 — 가장 단순한 뼈대만 먼저 동작시킨다.
    call_llm()이 재시도 끝에 실패하면(완전 실패) 예외를 그대로 전파한다
    (질문 분석 노드와 동일 원칙 — 인프라 장애는 숨기지 않는다).
    """
    question = state["question"]
    store = state["store"]

    summary = call_llm(SYSTEM_PROMPT, build_user_prompt(question, store)).strip()
    if not summary:
        raise ValueError("LLM이 빈 전략 요약을 반환했습니다.")

    return {"result": {"summary": summary}}
