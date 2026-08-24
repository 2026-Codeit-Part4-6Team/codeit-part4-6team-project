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

    SDP §6.1 파이프라인 순서를 따르되, suggested_chips·market_for_consult·
    trend_for_consult는 서로의 결과를 쓰지 않아 question_analysis 직후 셋 다 병렬로
    갈라졌다가 strategy 앞에서 합류한다(v2 섹션F는 market·trend 2-way였고, v3
    섹션F에서 suggested_chips까지 포함한 3-way로 확장했다 — suggested_chips는
    question_analysis의 결과(question·store·missing_info)만 필요하고 market/trend
    결과를 쓰지 않아, 그 앞에서 순차로 기다릴 이유가 애초에 없었다).
    context(merge_dicts)·sources(operator.add) reducer가 이미 병렬 쓰기를 지원하도록
    설계돼 있다. suggested_chips는 tokens_used를 갱신하지만 market_for_consult·
    trend_for_consult 둘 다 이 필드를 건드리지 않아(외부 API만 호출, LLM 호출 없음)
    세 노드가 병렬로 묶여도 tokens_used를 쓰는 노드는 suggested_chips 하나뿐이라
    충돌 여지가 없다.

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
    graph.add_edge("question_analysis", "market_for_consult")
    graph.add_edge("question_analysis", "trend_for_consult")
    # 개별 add_edge 3개(X→strategy)는 셋 다 strategy의 같은 branch-to 채널에 쓸
    # 뿐이라 "모두 완료 후 1회 실행"이 공식적으로 보장되지 않는다 — LangGraph는
    # 리스트 폼일 때만 별도 join 채널(NamedBarrierValue)을 만들어 이를 보장한다
    # (v2 섹션F Codex 리뷰, LangGraph 소스 확인).
    graph.add_edge(["suggested_chips", "market_for_consult", "trend_for_consult"], "strategy")
    graph.add_edge("strategy", "strategy_check")
    graph.add_edge("strategy_check", "security_output")
    graph.add_edge("security_output", "self_check_node")
    graph.add_edge("self_check_node", END)

    return graph.compile()
