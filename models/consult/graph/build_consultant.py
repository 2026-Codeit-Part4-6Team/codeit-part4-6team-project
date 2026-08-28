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


def route_after_security_input(state: ConsultState) -> str:
    """입력 검증이 warn·block이면 종료하고, pass면 질문 분석으로 진행한다."""
    return "end" if state.get("status") == "blocked" else "question_analysis"


def route_after_security_output(state: ConsultState) -> str:
    """출력 검증이 block이면 종료하고, 나머지는 self_check로 진행한다."""
    return "end" if state.get("status") == "blocked" else "self_check_node"


def route_after_self_check(state: ConsultState) -> str:
    """reject는 전략을 1회 재생성하고, pass·warn·재실패는 종료한다."""
    if state.get("status") in ("blocked", "error"):
        return "end"
    verdict = (state.get("validation") or {}).get("self_check") or {}
    return "strategy" if verdict.get("action") == "reject" else "end"


def build_consultant() -> CompiledStateGraph:
    """검증과 데이터 조회를 포함한 컨설턴트 챗봇 그래프를 조립한다.

    SDP §6.1 파이프라인 순서를 따르되, market_for_consult·trend_for_consult는 서로의
    결과를 쓰지 않아 suggested_chips 직후 병렬로 갈라졌다가 strategy 앞에서 합류한다
    (v2 섹션F). context(merge_dicts)·sources(operator.add) reducer가 이미 병렬 쓰기를
    지원하도록 설계돼 있고, 두 노드 다 tokens_used를 건드리지 않아 충돌 여지가 없다.

    [이 전략으로 광고 만들기] 연계는 이 그래프에 없다. 서비스 계층이 저장된 결과를
    조회·재검증해 source_context로 조립하는 전적으로 서비스 책임이라(D-363·D-366,
    SDP §6.3), 모델 쪽에는 대응 노드가 없다. 빈 스텁이던 link_to_ads.py도 D8에서
    삭제했다.

    검증 3종은 조건부 엣지로 연결한다. 입력 warn·block은 LLM 호출 전에 끝내고,
    출력 block은 결과를 폐기했으므로 self_check를 건너뛴다. self_check reject만
    strategy로 되돌아가며 재생성 상한은 1회다(SELF_CHECK_MAX_RETRY, 검증 계약 V-03).
    재생성 경로는 suggested_chips·market·trend를 건너뛰므로 추가 비용은 strategy
    LLM 1회뿐이고, 상한 초과 시 self_check_node가 status="error"를 설정해 종료한다.
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
    graph.add_conditional_edges(
        "security_input",
        route_after_security_input,
        {"question_analysis": "question_analysis", "end": END},
    )
    graph.add_edge("question_analysis", "suggested_chips")
    graph.add_edge("suggested_chips", "market_for_consult")
    graph.add_edge("suggested_chips", "trend_for_consult")
    # 개별 add_edge 2개(market_for_consult→strategy, trend_for_consult→strategy)는
    # 둘 다 strategy의 같은 branch-to 채널에 쓸 뿐이라 "모두 완료 후 1회 실행"이
    # 공식적으로 보장되지 않는다 — LangGraph는 리스트 폼일 때만 별도 join 채널
    # (NamedBarrierValue)을 만들어 이를 보장한다(Codex 리뷰, LangGraph 소스 확인).
    graph.add_edge(["market_for_consult", "trend_for_consult"], "strategy")
    graph.add_edge("strategy", "strategy_check")
    graph.add_edge("strategy_check", "security_output")
    graph.add_conditional_edges(
        "security_output",
        route_after_security_output,
        {"self_check_node": "self_check_node", "end": END},
    )
    graph.add_conditional_edges(
        "self_check_node",
        route_after_self_check,
        {"strategy": "strategy", "end": END},
    )

    return graph.compile()
