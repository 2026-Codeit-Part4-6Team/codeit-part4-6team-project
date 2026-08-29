# 보안1(입력 검증) 노드 — 전민재 PM의 check_input()을 감싸는 자리
import time

from models.consult.graph.state import ConsultState
from models.shared.config import LLM_DEADLINE_SECONDS
from validation.security import check_input


def security_input(state: ConsultState) -> dict:
    """사용자 원본 질문을 검증하고 warn·block이면 LLM 호출 전에 종료한다.

    warn은 사용자가 질문을 보완하도록 reask로, block은 정책 차단으로 변환한다.
    두 경우 모두 status="blocked"라 서비스가 크레딧을 롤백할 수 있다.

    그래프 첫 노드라 여기서 state["deadline"]을 1회 세팅한다 — 이후 모든 call_llm
    호출이 이 값을 공유해, strategy의 재시도(최대 3회)+429 백오프가 겹쳐도 서비스
    60초 타임아웃에 근접하지 않도록 그래프 전체가 하나의 예산을 쓴다(D-144, PM 리뷰 PR #93).
    """
    verdict = check_input(state["question"])
    updates = {
        "validation": {**state.get("validation", {}), "input": verdict},
        "deadline": time.monotonic() + LLM_DEADLINE_SECONDS,
    }

    action = verdict.get("action")
    if action == "pass":
        return updates

    updates["status"] = "blocked"
    updates["issues"] = state.get("issues", []) + [
        {
            "source": "input",
            "action": "block" if action == "block" else "reask",
            "reason": (
                "illegal_or_injection" if action == "block" else "need_clarification"
            ),
            "message": verdict.get("message", ""),
        }
    ]
    return updates
