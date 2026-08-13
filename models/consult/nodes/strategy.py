# 마케팅 전략 제안 노드 (가장 중요) — D4 섹션 1~3
from models.consult.graph.state import ConsultState
from models.consult.prompts.strategy import SYSTEM_PROMPT, build_user_prompt
from models.shared.llm import call_llm


def strategy(state: ConsultState) -> dict:
    """질문·가게 정보·(있으면) 상권 데이터로 전략 요약을 생성한다.

    상권 데이터(context["market"])가 없으면(조회 실패, 노드 조기 실행 등) 프롬프트에서
    해당 섹션이 통째로 빠지고 질문·가게 정보만으로 생성한다 — 부분 성공 허용 원칙.
    트렌드 데이터 연동(D5/D6)은 아직 하지 않는다. actions 구조화(섹션 4), 근거
    필수화(섹션 5)도 다음 단계다.
    call_llm()이 재시도 끝에 실패하면(완전 실패) 예외를 그대로 전파한다
    (질문 분석 노드와 동일 원칙 — 인프라 장애는 숨기지 않는다).
    이번 호출의 토큰 사용량은 state["tokens_used"]에 누적한다.
    """
    question = state["question"]
    store = state["store"]
    market = state.get("context", {}).get("market")

    text, tokens = call_llm(SYSTEM_PROMPT, build_user_prompt(question, store, market))
    summary = text.strip()
    if not summary:
        raise ValueError("LLM이 빈 전략 요약을 반환했습니다.")

    return {
        "result": {"summary": summary},
        "tokens_used": state.get("tokens_used", 0) + tokens,
    }
