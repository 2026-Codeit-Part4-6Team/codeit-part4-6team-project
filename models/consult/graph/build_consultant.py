# models/consult/graph/build_consultant.py — 컨설턴트 챗봇 LangGraph 골격
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from models.consult.graph.state import ConsultState
from models.consult.nodes.market_for_consult import market_for_consult
from models.consult.nodes.question_analysis import question_analysis
from models.consult.nodes.seasonality_for_consult import seasonality_for_consult
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

    SDP §6.1 파이프라인 순서를 따르되, suggested_chips·market_for_consult·
    trend_for_consult·seasonality_for_consult는 서로의 결과를 쓰지 않아
    question_analysis 직후 넷 다 병렬로 갈라졌다가 strategy 앞에서 합류한다(v2
    섹션F는 market·trend 2-way였고, v3 섹션F에서 suggested_chips까지 포함한
    3-way로, 섹션C에서 seasonality_for_consult까지 포함한 4-way로 확장했다 —
    seasonality_for_consult는 날짜만으로 계산하는 순수 함수라 question_analysis의
    결과조차 필요 없다).
    context(merge_dicts)·sources(operator.add) reducer가 이미 병렬 쓰기를 지원하도록
    설계돼 있다. suggested_chips는 tokens_used를 갱신하지만 market_for_consult·
    trend_for_consult·seasonality_for_consult는 이 필드를 건드리지 않아(외부 API
    또는 순수 계산만 사용, LLM 호출 없음), 네 노드가 병렬로 묶여도 tokens_used를
    쓰는 노드는 suggested_chips 하나뿐이라 충돌 여지가 없다.

    받아들인 트레이드오프(Codex 리뷰): suggested_chips의 LLM 호출이 인프라 장애로
    완전 실패(재시도 소진)하면 예외가 그대로 전파되는데(suggested_chips.py 참고 —
    question_analysis/strategy와 동일 원칙, "인프라 장애는 숨기지 않는다"), 이제는
    market_for_consult·trend_for_consult가 question_analysis 직후 이미 병렬로
    시작된 상태라 그 외부 API 호출(공공데이터포털 상권 API·네이버 트렌드 API)이
    이미 소비된 뒤일 수 있다. v2까지는 suggested_chips가 market/trend보다 앞이라
    이 경우 두 API를 아예 안 불렀다. 어차피 이 실패는 최종 응답을 error로 만들어
    사용자 경험은 동일하고, 낭비되는 건 LLM 토큰이 아니라 여유 있는 외부 API
    호출량뿐이라 허용하기로 했다 — 인프라 장애가 잦아지거나 API 한도가 빠듯해지면
    재검토한다.

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
    graph.add_node("seasonality_for_consult", seasonality_for_consult)
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
    graph.add_edge("question_analysis", "market_for_consult")
    graph.add_edge("question_analysis", "trend_for_consult")
    graph.add_edge("question_analysis", "seasonality_for_consult")
    # 개별 add_edge 4개(X→strategy)는 넷 다 strategy의 같은 branch-to 채널에 쓸
    # 뿐이라 "모두 완료 후 1회 실행"이 공식적으로 보장되지 않는다 — LangGraph는
    # 리스트 폼일 때만 별도 join 채널(NamedBarrierValue)을 만들어 이를 보장한다
    # (v2 섹션F Codex 리뷰, LangGraph 소스 확인).
    graph.add_edge(
        ["suggested_chips", "market_for_consult", "trend_for_consult", "seasonality_for_consult"],
        "strategy",
    )
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
