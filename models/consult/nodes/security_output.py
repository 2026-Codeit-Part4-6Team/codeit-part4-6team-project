# 보안2(출력 검증) 노드 — 전민재 PM의 check_output()을 감싸는 자리
from models.consult.graph.state import ConsultState
from validation.security import check_output


def security_output(state: ConsultState) -> dict:
    """생성된 전략 텍스트(summary+actions+reasons)를 check_output()으로 검증하고
    판정 결과를 저장한다.

    summary만이 아니라 actions[].content·reasons[]도 사용자에게 그대로 노출되므로
    셋을 합쳐서 검증한다 — summary만 넘기면 actions/reasons에 섞여든 문제 표현이
    검증을 거치지 않고 그대로 응답에 나갈 수 있다(PM 리뷰, PR #93).

    result가 아직 채워지지 않은 상태(그래프 조기 실행 등)에서도 죽지 않도록
    빈 문자열로 안전하게 폴백한다. check_output()은 아직 pass 스텁이라 항상 통과한다.

    이번 섹션에서는 판정 결과를 저장하는 것까지만 구현하기로 합의했다 —
    block/warn 판정을 실제로 반영하는 로직은 PM 실구현 연동 시점에 함께 추가한다.

    TODO(PM 실구현 후): block/warn 판정을 이후 노드나 최종 응답에 실제로
    반영하는 로직을 추가할 것.
    """
    result = state.get("result", {})
    summary = result.get("summary", "")
    action_texts = [a.get("content", "") for a in result.get("actions", []) if isinstance(a, dict)]
    reasons = result.get("reasons", [])
    validated_text = "\n".join(part for part in [summary, *action_texts, *reasons] if part)

    validation_result = check_output(validated_text)
    return {"validation": {"output": validation_result}}
