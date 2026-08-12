# model_consult/graph/build_consultant.py — 컨설턴트 챗봇 LangGraph 골격
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from model_consult.graph.state import ConsultState
from model_consult.nodes.market_for_consult import market_for_consult
from model_consult.nodes.question_analysis import question_analysis
from model_consult.nodes.security_input import security_input
from model_consult.nodes.security_output import security_output
from model_consult.nodes.self_check_node import self_check_node
from model_consult.nodes.strategy import strategy
from model_consult.nodes.strategy_check import strategy_check
from model_consult.nodes.suggested_chips import suggested_chips
from model_consult.nodes.trend_for_consult import trend_for_consult


def build_consultant() -> CompiledStateGraph:
    """빈 노드로 START→END까지 연결된 컨설턴트 챗봇 그래프를 조립한다.

    지금은 SDP §6.1 파이프라인 순서대로 순차 연결만 한다. 병렬 조회(상권/트렌드)나
    재생성 조건부 엣지는 해당 노드에 실제 로직이 들어가는 이후 섹션에서 추가한다.

    link_to_ads는 기본 경로에 연결하지 않는다. SDP §6.3상 사용자가 [이 전략으로
    광고 만들기] 버튼을 눌렀을 때만 호출돼야 하는데, 기본 경로에 넣으면 모든 상담
    요청마다 자동 호출된다. D8에서 실제 트리거 조건이 정해지면 조건부 엣지 또는
    별도 진입점으로 연결한다.
    """
    graph = StateGraph(ConsultState)

    graph.add_node("security_input", security_input)
    graph.add_node("question_analysis", question_analysis)
    graph.add_node("suggested_chips", suggested_chips)
    graph.add_node("market_for_consult", market_for_consult)
    graph.add_node("trend_for_consult", trend_for_consult)
    graph.add_node("strategy", strategy)
    graph.add_node("strategy_check", strategy_check)
    graph.add_node("security_output", security_output)
    graph.add_node("self_check_node", self_check_node)

    graph.add_edge(START, "security_input")
    graph.add_edge("security_input", "question_analysis")
    graph.add_edge("question_analysis", "suggested_chips")
    graph.add_edge("suggested_chips", "market_for_consult")
    graph.add_edge("market_for_consult", "trend_for_consult")
    graph.add_edge("trend_for_consult", "strategy")
    graph.add_edge("strategy", "strategy_check")
    graph.add_edge("strategy_check", "security_output")
    graph.add_edge("security_output", "self_check_node")
    graph.add_edge("self_check_node", END)

    return graph.compile()
