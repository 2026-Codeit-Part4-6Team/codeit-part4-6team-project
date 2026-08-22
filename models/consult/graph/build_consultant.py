# models/consult/graph/build_consultant.py — 컨설턴트 챗봇 LangGraph 골격
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from models.consult.graph.state import ConsultState
from models.consult.nodes.market_for_consult import market_for_consult
from models.consult.nodes.question_analysis import question_analysis
from models.consult.nodes.security_input import security_input
from models.consult.nodes.security_output import security_output
from models.consult.nodes.self_check_node import self_check_node
from models.consult.nodes.strategy import strategy
from models.consult.nodes.strategy_check import strategy_check
from models.consult.nodes.suggested_chips import suggested_chips
from models.consult.nodes.trend_for_consult import trend_for_consult


def build_consultant() -> CompiledStateGraph:
    """빈 노드로 START→END까지 연결된 컨설턴트 챗봇 그래프를 조립한다.

    지금은 SDP §6.1 파이프라인 순서대로 순차 연결만 한다. 병렬 조회(상권/트렌드)나
    재생성 조건부 엣지는 해당 노드에 실제 로직이 들어가는 이후 섹션에서 추가한다.

    [이 전략으로 광고 만들기] 연계는 이 그래프에 없다 — 서비스 계층이 저장된 결과를
    조회·재검증해 source_context로 조립하는 전적으로 서비스 책임이라(D-363·D-366,
    SDP §6.3), 모델 쪽엔 대응 노드가 없다. 기존 link_to_ads.py(빈 스텁)는 이 결정으로
    D8에서 삭제했다.
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
