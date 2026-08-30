"""D3 기본 카피/이미지 생성 파이프라인의 LangGraph 그래프 정의.

security_input → question_analysis → (channel/market/trend/benchmark/seasonality
컨텍스트 수집) → copy_gen → ranking → regulation → image_gen → image_review
→ channel_format → security_output → self_check 순으로 노드를 연결하며, 각 단계
실패 시 재시도(COPY_MAX_RETRY/IMAGE_MAX_RETRY) 또는 조기 종료(end_blocked)로
분기한다.
"""

from langgraph.graph import END, START, StateGraph

from ..config import COPY_MAX_RETRY, IMAGE_MAX_RETRY
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
from ..nodes.seasonality_for_copy import seasonality_for_copy_node
from ..nodes.security_input import security_input_node
from ..nodes.security_output import security_output_node
from ..nodes.self_check_node import self_check_node
from ..nodes.trend_for_copy import trend_for_copy_node
from .state import BasicState

# 조건부 라우팅 함수 (상태 읽기)


def route_after_security_input(state: BasicState) -> str:
    """입력 보안 검사 결과가 차단이면 종료, 아니면 질문 분석으로 진행한다."""
    result = (state.get("validation") or {}).get("input") or {}
    return "end_blocked" if result.get("action") == "block" else "question_analysis"


def route_after_question_analysis(state: BasicState) -> str:
    """질문 분석 결과 상태가 blocked면 종료, 아니면 채널 노드로 진행한다."""
    return "end_blocked" if state.get("status") in ("blocked", "error") else "channel"


def route_after_copy_gen(state: BasicState) -> str:
    """카피 후보가 전부 생성 실패면 재시도 한도 내에서 copy_gen을 반복하고,
    한도를 넘기면 종료한다. 하나라도 성공하면 ranking으로 진행한다."""
    if state.get("status") == "error":
        return "end_blocked"
    candidates = state.get("copy_candidates") or []
    all_failed = bool(candidates) and all(c.get("copy") is None for c in candidates)
    if all_failed:
        if state.get("copy_retry_count", 0) >= COPY_MAX_RETRY:
            return "end_blocked"
        return "copy_gen"
    return "ranking"


def route_after_ranking(state: BasicState) -> str:
    """랭킹이 LLM 호출 오류로 실패하면 종료, 아니면 regulation으로 진행한다."""
    return "end_blocked" if state.get("status") == "error" else "regulation"


def route_after_regulation(state: BasicState) -> str:
    """규제 검수가 차단이면 재시도 한도 내에서 copy_gen으로 되돌리고,
    한도를 넘기면 종료한다(warn도 pass가 하나도 없으면 재생성 대상이다).
    통과하면 image_gen으로 진행한다."""
    result = (state.get("validation") or {}).get("regulation") or {}
    if result.get("action") in ("block", "warn"):
        if state.get("copy_retry_count", 0) >= COPY_MAX_RETRY:
            return "end_blocked"
        return "copy_gen"
    return "image_gen"


def route_after_image_review(state: BasicState) -> str:
    """이미지 디코딩이 전부 실패하면 이미지 재생성 상한(1회) 내에서 image_gen을
    반복하고, 그 외(이미지 없음·낮은 CLIP 점수 포함)에는 차단하지 않고 진행한다."""
    result = state.get("image_review_result") or {}
    if result.get("action") == "reject":
        if state.get("image_retry_count", 0) >= IMAGE_MAX_RETRY:
            return "channel_format"
        return "image_gen"
    return "channel_format"


def route_after_self_check(state: BasicState) -> str:
    """자가 점검이 반려면 즉시 종료한다(SELF_CHECK_MAX_RETRY=0 — 재시도
    없이 차단, D-413). 그 외는 정상 종료한다."""
    result = (state.get("validation") or {}).get("self_check") or {}
    return "end_blocked" if result.get("action") == "reject" else "__end__"


def build_basic_graph():
    """D3 파이프라인의 모든 노드와 조건부 라우팅을 연결한 StateGraph를 컴파일해 반환한다."""
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
    graph.add_node("seasonality_for_copy", seasonality_for_copy_node)
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
    graph.add_edge("benchmark", "seasonality_for_copy")
    graph.add_edge("seasonality_for_copy", "copy_gen")

    # 카피 생성, 랭킹 및 규제 검수
    graph.add_conditional_edges(
        "copy_gen",
        route_after_copy_gen,
        {"copy_gen": "copy_gen", "ranking": "ranking", "end_blocked": END},
    )

    graph.add_conditional_edges(
        "ranking",
        route_after_ranking,
        {"regulation": "regulation", "end_blocked": END},
    )

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
