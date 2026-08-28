# ConsultState 필드 구성 테스트
from langgraph.graph import END, START, StateGraph

from models.consult.graph.state import ConsultState
from models.shared.state_common import CommonState


def test_consult_state_extends_common_state() -> None:
    """ConsultState는 CommonState 필드를 전부 포함한다."""
    assert set(CommonState.__annotations__.keys()) <= set(
        ConsultState.__annotations__.keys()
    )


def test_consult_state_has_consult_specific_fields() -> None:
    """컨설턴트 전용 필드(재생성 루프·추천 질문 칩·LLM 호출 공유 마감)가 갖춰져 있다.

    전략 결과는 별도 필드 없이 상속받은 result에 담으므로 여기 포함되지 않는다.
    """
    consult_only = set(ConsultState.__annotations__.keys()) - set(
        CommonState.__annotations__.keys()
    )
    assert consult_only == {
        "retry_count",
        "self_check_retry_count",
        "actions_retried",
        "actions_truncated",
        "suggested_chips",
        "deadline",
        "chips_fallback",
        "status",
        "issues",
    }


def test_consult_specific_fields_are_not_required() -> None:
    """재생성 루프 카운터 등은 파이프라인이 나중에 채우므로 최초 상태 생성 시 필수가 아니어야 한다."""
    consult_only = {
        "retry_count",
        "self_check_retry_count",
        "actions_retried",
        "actions_truncated",
        "suggested_chips",
        "deadline",
        "chips_fallback",
        "status",
        "issues",
    }
    assert consult_only <= ConsultState.__optional_keys__
    assert ConsultState.__required_keys__ == CommonState.__required_keys__


def test_status_and_issues_survive_langgraph_execution() -> None:
    """ConsultState가 status·issues를 선언하지 않으면 LangGraph가 스키마에 없는 키를
    조용히 버린다 — 노드가 blocked/error를 반환해도 assemble_response()가 절대 보지
    못하는 치명적 버그였다(Codex 리뷰로 발견). 최소 그래프로 실제 LangGraph 동작을
    검증한다 — mock으로 dict만 비교하면 이 스키마 누락을 잡지 못한다."""

    def fake_node(state: ConsultState) -> dict:
        return {
            "status": "blocked",
            "issues": [{"source": "input", "action": "block", "reason": "x", "message": "m"}],
        }

    graph = StateGraph(ConsultState)
    graph.add_node("fake", fake_node)
    graph.add_edge(START, "fake")
    graph.add_edge("fake", END)
    compiled = graph.compile()

    result = compiled.invoke(
        {
            "chatbot_type": "consultant",
            "user_id": 1,
            "question": "질문",
            "store": {"name": "n", "type": "t", "address": "a", "lat": 0.0, "lng": 0.0},
        }
    )

    assert result["status"] == "blocked"
    assert result["issues"] == [
        {"source": "input", "action": "block", "reason": "x", "message": "m"}
    ]
