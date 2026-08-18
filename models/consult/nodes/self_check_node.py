# self_check 노드 — 전민재 PM의 self_check()를 감싸는 자리
from models.consult.graph.state import ConsultState
from validation.self_check import self_check


def self_check_node(state: ConsultState) -> dict:
    """전략 결과와 컨텍스트를 self_check()로 검증하고 판정 결과를 저장한다.

    result·context가 아직 채워지지 않은 상태에서도 죽지 않도록 빈 dict로
    안전하게 폴백한다. self_check()는 아직 pass 스텁이라 항상 통과한다.

    이번 섹션에서는 판정 결과를 저장하는 것까지만 구현하기로 합의했다 —
    reject 판정을 실제로 반영하는 로직은 PM 실구현 연동 시점에 함께 추가한다.

    TODO(PM 실구현 후): reject 판정을 재생성 루프나 최종 응답에 실제로
    반영하는 로직을 추가할 것.
    """
    result = state.get("result", {})
    context = state.get("context", {})
    check = self_check(result, context)
    return {"validation": {"self_check": check}}
