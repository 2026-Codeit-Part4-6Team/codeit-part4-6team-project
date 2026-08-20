# build_consultant 그래프 골격 테스트
import json
from unittest.mock import patch

from models.consult.graph.build_consultant import build_consultant


def _initial_state() -> dict:
    return {
        "chatbot_type": "consultant",
        "user_id": 1,
        "question": "우리 카페 어떻게 홍보하면 좋을까요?",
        "store": {
            "name": "카페 코드잇",
            "type": "카페",
            "address": "서울 강남구 역삼동",
            "lat": 37.5,
            "lng": 127.0,
        },
    }


@patch("models.consult.nodes.strategy.call_llm")
@patch("models.consult.nodes.question_analysis.call_llm")
def test_graph_runs_start_to_end_without_error(
    mock_question_call_llm, mock_strategy_call_llm
) -> None:
    """실제 로직이 채워진 노드(question_analysis, strategy)를 포함해도 START→END까지 끊김 없이 실행된다."""
    mock_question_call_llm.return_value = (
        json.dumps(
            {
                "rewritten_question": "우리 카페 어떻게 홍보하면 좋을까요?",
                "is_sufficient": True,
                "missing_info": [],
            }
        ),
        100,
    )
    mock_strategy_call_llm.return_value = (
        json.dumps(
            {
                "summary": "시즌 한정 메뉴로 신규 고객을 유입하세요.",
                "actions": [{"type": "menu", "content": "시즌 한정 메뉴 도입"}],
                "reasons": ["반경 내 동일 업종이 12곳으로 밀도 등급이 '높음'입니다"],
            }
        ),
        100,
    )
    graph = build_consultant()

    result = graph.invoke(_initial_state())

    assert result["question"] == "우리 카페 어떻게 홍보하면 좋을까요?"
    assert result["result"]["summary"] == "시즌 한정 메뉴로 신규 고객을 유입하세요."


def test_default_path_skips_link_to_ads() -> None:
    """link_to_ads는 사용자가 버튼을 눌렀을 때만 호출돼야 하므로 기본 경로에 없어야 한다."""
    drawable = build_consultant().get_graph()

    assert "link_to_ads" not in drawable.nodes

    edges = {(edge.source, edge.target) for edge in drawable.edges}
    assert ("strategy_check", "security_output") in edges
    assert ("strategy_check", "link_to_ads") not in edges


def test_default_path_has_expected_topology() -> None:
    """빈 노드 9개가 SDP §6.1 순서 그대로 START→END로 순차 연결돼 있어야 한다."""
    drawable = build_consultant().get_graph()

    assert set(drawable.nodes.keys()) == {
        "__start__",
        "__end__",
        "security_input",
        "question_analysis",
        "suggested_chips",
        "market_for_consult",
        "trend_for_consult",
        "strategy",
        "strategy_check",
        "security_output",
        "self_check_node",
    }

    edges = {(edge.source, edge.target) for edge in drawable.edges}
    assert edges == {
        ("__start__", "security_input"),
        ("security_input", "question_analysis"),
        ("question_analysis", "suggested_chips"),
        ("suggested_chips", "market_for_consult"),
        ("market_for_consult", "trend_for_consult"),
        ("trend_for_consult", "strategy"),
        ("strategy", "strategy_check"),
        ("strategy_check", "security_output"),
        ("security_output", "self_check_node"),
        ("self_check_node", "__end__"),
    }
