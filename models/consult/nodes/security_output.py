# 보안2(출력 검증) 노드 — 전민재 PM의 check_output()을 감싸는 자리
from models.consult.graph.state import ConsultState
from validation.security import check_output


def security_output(state: ConsultState) -> dict:
    """생성된 전략 요약 텍스트를 check_output()으로 검증하고 판정 결과를 저장한다.

    result가 아직 채워지지 않은 상태(그래프 조기 실행 등)에서도 죽지 않도록
    빈 문자열로 안전하게 폴백한다. check_output()은 아직 pass 스텁이라 항상 통과한다.

    이번 섹션에서는 판정 결과를 저장하는 것까지만 구현하기로 합의했다 —
    block/warn 판정을 실제로 반영하는 로직은 PM 실구현 연동 시점에 함께 추가한다.

    TODO(PM 실구현 후): block/warn 판정을 이후 노드나 최종 응답에 실제로
    반영하는 로직을 추가할 것.
    """
    summary = state.get("result", {}).get("summary", "")
    result = check_output(summary)
    return {"validation": {"output": result}}
