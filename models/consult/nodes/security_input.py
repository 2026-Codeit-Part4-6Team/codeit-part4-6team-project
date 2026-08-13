# 보안1(입력 검증) 노드 — 전민재 PM의 check_input()을 감싸는 자리
from models.consult.graph.state import ConsultState
from validation.security import check_input


def security_input(state: ConsultState) -> dict:
    """사용자 원본 질문을 check_input()으로 검증하고 판정 결과를 저장한다.

    check_input()은 아직 pass 스텁이라 항상 통과한다. 이번 섹션에서는 판정
    결과를 state["validation"]["input"]에 저장하는 것까지만 구현하기로 합의했다
    — block 판정 시 파이프라인을 실제로 중단시키는 로직은 PM 실구현 연동
    시점에 함께 추가한다.

    TODO(PM 실구현 후): block 판정이면 이후 노드로 진행하지 않고 즉시 응답을
    반환하도록 그래프에 조건부 엣지를 추가할 것.
    """
    result = check_input(state["question"])
    return {"validation": {"input": result}}
