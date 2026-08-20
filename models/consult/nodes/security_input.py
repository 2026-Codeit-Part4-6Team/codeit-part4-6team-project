# 보안1(입력 검증) 노드 — 전민재 PM의 check_input()을 감싸는 자리
import time

from models.consult.graph.state import ConsultState
from models.shared.config import LLM_DEADLINE_SECONDS
from validation.security import check_input


def security_input(state: ConsultState) -> dict:
    """사용자 원본 질문을 check_input()으로 검증하고 판정 결과를 저장한다.

    check_input()은 아직 pass 스텁이라 항상 통과한다. 이번 섹션에서는 판정
    결과를 state["validation"]["input"]에 저장하는 것까지만 구현하기로 합의했다
    — block 판정 시 파이프라인을 실제로 중단시키는 로직은 PM 실구현 연동
    시점에 함께 추가한다.

    TODO(PM 실구현 후): block 판정이면 이후 노드로 진행하지 않고 즉시 응답을
    반환하도록 그래프에 조건부 엣지를 추가할 것.

    그래프 첫 노드라 여기서 state["deadline"]을 1회 세팅한다 — 이후 모든 call_llm
    호출이 이 값을 공유해, strategy의 재시도(최대 3회)+429 백오프가 겹쳐도 서비스
    60초 타임아웃에 근접하지 않도록 그래프 전체가 하나의 예산을 쓴다(D-144, PM 리뷰 PR #93).
    """
    result = check_input(state["question"])
    return {
        "validation": {"input": result},
        "deadline": time.monotonic() + LLM_DEADLINE_SECONDS,
    }
