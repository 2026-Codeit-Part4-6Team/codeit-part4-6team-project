from langgraph.graph import END, START, StateGraph

from ..nodes.benchmark_node import benchmark_node
from ..nodes.channel import channel_node
from ..nodes.channel_format import channel_format_node
from ..nodes.copy_gen import copy_gen_node
from ..nodes.image_gen import image_gen_node
from ..nodes.image_review import image_review_node
from ..nodes.market_for_copy import market_for_copy_node
from ..nodes.question_analysis import question_analysis_node
from ..nodes.ranking import ranking_node
from ..nodes.regulation_node import regulation_node
from ..nodes.security_input import security_input_node
from ..nodes.security_output import security_output_node
from ..nodes.self_check_node import self_check_node
from ..nodes.trend_for_copy import trend_for_copy_node
from .state import BasicState

MAX_RETRY = 2

# 조건부 라우팅 함수 (상태 읽기)


def route_after_security_input(state: BasicState) -> str:
    result = (state.get("validation") or {}).get("input") or {}
    return "end_blocked" if result.get("action") == "block" else "question_analysis"


def route_after_question_analysis(state: BasicState) -> str:
    return "end_blocked" if state.get("status") == "blocked" else "channel"


def route_after_copy_gen(state: BasicState) -> str:
    candidates = state.get("copy_candidates") or []
    all_failed = bool(candidates) and all(c.get("copy") is None for c in candidates)
    if all_failed:
        if state.get("retry_count", 0) >= MAX_RETRY:
            return "end_blocked"
        return "copy_gen"
    return "ranking"


def route_after_regulation(state: BasicState) -> str:
    result = (state.get("validation") or {}).get("regulation") or {}
    if result.get("action") == "block":
        if state.get("retry_count", 0) >= MAX_RETRY:
            return "end_blocked"
        return "copy_gen"
    return "image_gen"


def route_after_image_review(state: BasicState) -> str:
    result = state.get("image_review_result") or {}
    if result.get("action") == "reject":
        if state.get("retry_count", 0) >= MAX_RETRY:
            return "channel_format"
        return "image_gen"
    return "channel_format"


def route_after_self_check(state: BasicState) -> str:
    result = (state.get("validation") or {}).get("self_check") or {}
    return "end_blocked" if result.get("action") == "reject" else "__end__"


def build_basic_graph():
    graph = StateGraph(BasicState)

    graph.add_node("benchmark", benchmark_node)
    graph.add_node("channel_format", channel_format_node)
    graph.add_node("channel", channel_node)
    graph.add_node("copy_gen", copy_gen_node)
    graph.add_node("image_gen", image_gen_node)
    graph.add_node("image_review", image_review_node)
    graph.add_node("market_for_copy", market_for_copy_node)
    graph.add_node("question_analysis", question_analysis_node)
    graph.add_node("ranking", ranking_node)
    graph.add_node("regulation", regulation_node)
    graph.add_node("security_input", security_input_node)
    graph.add_node("security_output", security_output_node)
    graph.add_node("self_check", self_check_node)
    graph.add_node("trend_for_copy", trend_for_copy_node)

    # 진입 및 입력 보안 점검
    graph.add_edge(START, "security_input")

    graph.add_conditional_edges(
        "security_input",
        route_after_security_input,
        {"question_analysis": "question_analysis", "end_blocked": END},
    )

    # 질문 분석 및 추가 정보 요청 루프
    graph.add_conditional_edges(
        "question_analysis",
        route_after_question_analysis,
        {"channel": "channel", "end_blocked": END},
    )

    # 컨텍스트 수집 3종
    graph.add_edge("channel", "market_for_copy")
    graph.add_edge("market_for_copy", "trend_for_copy")
    graph.add_edge("trend_for_copy", "benchmark")
    graph.add_edge("benchmark", "copy_gen")

    # 카피 생성, 랭킹 및 규제 검수
    graph.add_conditional_edges(
        "copy_gen",
        route_after_copy_gen,
        {"copy_gen": "copy_gen", "ranking": "ranking", "end_blocked": END},
    )
    graph.add_edge("ranking", "regulation")

    graph.add_conditional_edges(
        "regulation",
        route_after_regulation,
        {"copy_gen": "copy_gen", "image_gen": "image_gen", "end_blocked": END},
    )

    # 이미지 생성 및 검수
    graph.add_edge("image_gen", "image_review")

    graph.add_conditional_edges(
        "image_review",
        route_after_image_review,
        {"image_gen": "image_gen", "channel_format": "channel_format"},
    )

    # 포맷팅, 출력 보안 검사 및 최종 자가 점검
    graph.add_edge("channel_format", "security_output")
    graph.add_edge("security_output", "self_check")

    graph.add_conditional_edges(
        "self_check",
        route_after_self_check,
        {"__end__": END, "end_blocked": END},
    )

    return graph.compile()
