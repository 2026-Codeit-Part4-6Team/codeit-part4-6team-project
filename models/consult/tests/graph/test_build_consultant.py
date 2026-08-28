# build_consultant 그래프 골격 테스트
import json
from importlib import import_module
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
@patch("models.consult.nodes.suggested_chips.call_llm")
@patch("models.consult.nodes.question_analysis.call_llm")
@patch("models.consult.nodes.trend_for_consult.get_trend")
@patch("models.consult.nodes.market_for_consult.get_market")
def test_graph_runs_start_to_end_without_error(
    mock_get_market,
    mock_get_trend,
    mock_question_call_llm,
    mock_chips_call_llm,
    mock_strategy_call_llm,
) -> None:
    """실제 로직이 채워진 노드(question_analysis, suggested_chips, strategy)를 포함해도
    START→END까지 끊김 없이 실행된다. market_for_consult·trend_for_consult는
    "둘 다 실패"를 환경변수 부재에 기대지 않고 명시적으로 mock해 재현한다 —
    실제 MARKET_API_KEY·NAVER_CLIENT_ID가 설정된 환경이나 해당 좌표가 이미
    캐싱된 환경에서는 조용히 성공해버려 이 테스트의 전제가 깨질 수 있다."""
    mock_get_market.return_value = None
    mock_get_trend.return_value = None
    mock_question_call_llm.return_value = (
        json.dumps(
            {
                "rewritten_question": "우리 카페 어떻게 홍보하면 좋을까요?",
                "is_sufficient": True,
                "missing_info": [],
                "keyword": "아이스아메리카노",
            }
        ),
        100,
    )
    mock_chips_call_llm.return_value = (
        json.dumps({"chips": ["질문 1", "질문 2", "질문 3"]}),
        50,
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
    mock_get_market.assert_called_once()
    mock_get_trend.assert_called_once()
    # market_for_consult·trend_for_consult가 둘 다 실패(None)해도 서비스 계약
    # (sources min_length=1)을 지키려면 strategy가 기본 출처로 채워야 한다.
    assert result["sources"] == ["가게정보"]


@patch("models.consult.nodes.strategy.call_llm")
@patch("models.consult.nodes.suggested_chips.call_llm")
@patch("models.consult.nodes.question_analysis.call_llm")
@patch("models.consult.nodes.trend_for_consult.get_trend")
@patch("models.consult.nodes.market_for_consult.get_market")
def test_graph_accumulates_sources_when_market_and_trend_both_succeed(
    mock_get_market,
    mock_get_trend,
    mock_question_call_llm,
    mock_chips_call_llm,
    mock_strategy_call_llm,
) -> None:
    """market_for_consult·trend_for_consult가 둘 다 성공하면 sources에 두 출처가
    모두 쌓이고, strategy는 기본 출처("가게정보")를 덧붙이지 않는다. strategy는 두
    조회가 모두 끝난 뒤 한 번만 실행돼야 한다(v2 섹션F 필수 동작). 호출 횟수 1회
    만으로는 "조기 실행 후 1회"까지는 못 잡으므로, 실제로 넘어간 프롬프트에 상권·
    트렌드 양쪽 고유값이 다 들어있는지도 확인한다(Codex 리뷰)."""
    mock_get_market.return_value = {
        "total_count": 43,
        "same_industry_count": 12,
        "nearest_distance_m": 55,
        "industry_breakdown": {"카페": 12},
    }
    mock_get_trend.return_value = {
        "keyword": "아이스아메리카노",
        "direction": "상승",
        "related": ["냉커피"],
        "weather": None,
    }
    mock_question_call_llm.return_value = (
        json.dumps(
            {
                "rewritten_question": "우리 카페 어떻게 홍보하면 좋을까요?",
                "is_sufficient": True,
                "missing_info": [],
                "keyword": "아이스아메리카노",
            }
        ),
        100,
    )
    mock_chips_call_llm.return_value = (
        json.dumps({"chips": ["질문 1", "질문 2", "질문 3"]}),
        50,
    )
    mock_strategy_call_llm.return_value = (
        json.dumps(
            {
                "summary": "요약",
                "actions": [{"type": "menu", "content": "액션"}],
                "reasons": ["근거"],
            }
        ),
        100,
    )
    graph = build_consultant()

    result = graph.invoke(_initial_state())

    assert result["sources"] == ["상권분석", "트렌드"]
    mock_strategy_call_llm.assert_called_once()
    _, strategy_user_prompt = mock_strategy_call_llm.call_args.args
    assert "12곳" in strategy_user_prompt
    assert "상승" in strategy_user_prompt


@patch("models.consult.nodes.strategy.call_llm")
@patch("models.consult.nodes.suggested_chips.call_llm")
@patch("models.consult.nodes.question_analysis.call_llm")
@patch("models.consult.nodes.trend_for_consult.get_trend")
@patch("models.consult.nodes.market_for_consult.get_market")
def test_graph_uses_trend_result_when_only_market_fails(
    mock_get_market,
    mock_get_trend,
    mock_question_call_llm,
    mock_chips_call_llm,
    mock_strategy_call_llm,
) -> None:
    """상권 조회만 실패해도 트렌드 결과로 strategy가 실행된다(v2 섹션F 병렬화
    후에도 부분 성공 허용 원칙이 유지되는지 확인)."""
    mock_get_market.return_value = None
    mock_get_trend.return_value = {
        "keyword": "아이스아메리카노",
        "direction": "상승",
        "related": ["냉커피"],
        "weather": None,
    }
    mock_question_call_llm.return_value = (
        json.dumps(
            {
                "rewritten_question": "우리 카페 어떻게 홍보하면 좋을까요?",
                "is_sufficient": True,
                "missing_info": [],
                "keyword": "아이스아메리카노",
            }
        ),
        100,
    )
    mock_chips_call_llm.return_value = (json.dumps({"chips": ["질문 1", "질문 2", "질문 3"]}), 50)
    mock_strategy_call_llm.return_value = (
        json.dumps({"summary": "요약", "actions": [{"type": "menu", "content": "액션"}], "reasons": ["근거"]}),
        100,
    )
    graph = build_consultant()

    result = graph.invoke(_initial_state())

    assert result["sources"] == ["트렌드"]
    assert result["context"]["market"] is None
    assert result["context"]["trend"]["direction"] == "상승"


@patch("models.consult.nodes.strategy.call_llm")
@patch("models.consult.nodes.suggested_chips.call_llm")
@patch("models.consult.nodes.question_analysis.call_llm")
@patch("models.consult.nodes.trend_for_consult.get_trend")
@patch("models.consult.nodes.market_for_consult.get_market")
def test_graph_uses_market_result_when_only_trend_fails(
    mock_get_market,
    mock_get_trend,
    mock_question_call_llm,
    mock_chips_call_llm,
    mock_strategy_call_llm,
) -> None:
    """트렌드 조회만 실패해도 상권 결과로 strategy가 실행된다(v2 섹션F)."""
    mock_get_market.return_value = {
        "total_count": 43,
        "same_industry_count": 12,
        "nearest_distance_m": 55,
        "industry_breakdown": {"카페": 12},
    }
    mock_get_trend.return_value = None
    mock_question_call_llm.return_value = (
        json.dumps(
            {
                "rewritten_question": "우리 카페 어떻게 홍보하면 좋을까요?",
                "is_sufficient": True,
                "missing_info": [],
                "keyword": "아이스아메리카노",
            }
        ),
        100,
    )
    mock_chips_call_llm.return_value = (json.dumps({"chips": ["질문 1", "질문 2", "질문 3"]}), 50)
    mock_strategy_call_llm.return_value = (
        json.dumps({"summary": "요약", "actions": [{"type": "menu", "content": "액션"}], "reasons": ["근거"]}),
        100,
    )
    graph = build_consultant()

    result = graph.invoke(_initial_state())

    assert result["sources"] == ["상권분석"]
    assert result["context"]["market"]["same_industry_count"] == 12
    assert result["context"]["trend"] is None


@patch("models.consult.nodes.strategy.call_llm")
@patch("models.consult.nodes.suggested_chips.call_llm")
@patch("models.consult.nodes.question_analysis.call_llm")
@patch("models.consult.nodes.trend_for_consult.get_trend")
@patch("models.consult.nodes.market_for_consult.get_market")
def test_market_and_trend_run_in_parallel_not_sequential(
    mock_get_market,
    mock_get_trend,
    mock_question_call_llm,
    mock_chips_call_llm,
    mock_strategy_call_llm,
) -> None:
    """market_for_consult·trend_for_consult가 실제로 동시에 실행되는지 확인한다.
    두 mock이 threading.Barrier(2)에서 서로를 기다리게 한다 — 순차 실행이면 먼저
    도착한 쪽이 둘째를 영원히 못 만나 타임아웃 예외를 던지고, 병렬 실행이면 둘 다
    거의 동시에 도착해 정상 통과한다. 절대 시간 임계값에 의존하지 않아 느린 CI에서
    정상적인 병렬 실행까지 실패로 오판하지 않는다(Codex 리뷰 — 기존 sleep+임계값
    비교는 느린 환경에서 flaky할 수 있다는 지적)."""
    import threading

    barrier = threading.Barrier(2, timeout=2.0)

    def rendezvous_market(*args, **kwargs):
        barrier.wait()

    def rendezvous_trend(*args, **kwargs):
        barrier.wait()

    mock_get_market.side_effect = rendezvous_market
    mock_get_trend.side_effect = rendezvous_trend
    mock_question_call_llm.return_value = (
        json.dumps(
            {
                "rewritten_question": "우리 카페 어떻게 홍보하면 좋을까요?",
                "is_sufficient": True,
                "missing_info": [],
                "keyword": "아이스아메리카노",
            }
        ),
        100,
    )
    mock_chips_call_llm.return_value = (json.dumps({"chips": ["질문 1", "질문 2", "질문 3"]}), 50)
    mock_strategy_call_llm.return_value = (
        json.dumps({"summary": "요약", "actions": [{"type": "menu", "content": "액션"}], "reasons": ["근거"]}),
        100,
    )
    graph = build_consultant()

    # 순차 실행이면 barrier.wait()이 타임아웃돼 BrokenBarrierError가 여기서 전파된다.
    graph.invoke(_initial_state())

    mock_get_market.assert_called_once()
    mock_get_trend.assert_called_once()


@patch("models.consult.nodes.question_analysis.call_llm")
@patch("models.consult.nodes.security_input.check_input")
def test_input_block_ends_before_any_question_llm(
    mock_check_input,
    mock_question_call_llm,
) -> None:
    mock_check_input.return_value = {
        "action": "block",
        "message": "처리할 수 없는 요청입니다.",
    }

    result = build_consultant().invoke(_initial_state())

    assert result["status"] == "blocked"
    assert result["issues"][0]["reason"] == "illegal_or_injection"
    mock_question_call_llm.assert_not_called()


@patch("models.consult.nodes.self_check_node.self_check")
@patch("models.consult.nodes.security_output.check_output")
@patch("models.consult.nodes.strategy.call_llm")
@patch("models.consult.nodes.suggested_chips.call_llm")
@patch("models.consult.nodes.question_analysis.call_llm")
@patch("models.consult.nodes.trend_for_consult.get_trend", return_value=None)
@patch("models.consult.nodes.market_for_consult.get_market", return_value=None)
def test_output_warn_masks_each_field_before_self_check(
    _mock_get_market,
    _mock_get_trend,
    mock_question_call_llm,
    mock_chips_call_llm,
    mock_strategy_call_llm,
    mock_check_output,
    mock_self_check,
) -> None:
    mock_question_call_llm.return_value = (
        json.dumps(
            {
                "rewritten_question": "우리 카페 홍보 전략",
                "is_sufficient": True,
                "missing_info": [],
                "keyword": None,
            }
        ),
        10,
    )
    mock_chips_call_llm.return_value = (
        json.dumps({"chips": ["질문 1", "질문 2", "질문 3"]}),
        10,
    )
    mock_strategy_call_llm.return_value = (
        json.dumps(
            {
                "title": "전략 제목",
                "summary": "요약 원문",
                "actions": [{"type": "promotion", "content": "액션 원문"}],
                "reasons": ["근거 원문"],
            }
        ),
        10,
    )
    mock_check_output.side_effect = lambda text: {
        "action": "warn",
        "message": "마스킹했습니다.",
        "masked_text": f"마스킹:{text}",
    }
    mock_self_check.return_value = {"action": "pass", "reasons": [], "message": ""}

    result = build_consultant().invoke(_initial_state())

    assert result["result"]["summary"] == "마스킹:요약 원문"
    assert result["result"]["actions"][0]["content"] == "마스킹:액션 원문"
    assert result["result"]["reasons"] == ["마스킹:근거 원문"]
    checked_result = mock_self_check.call_args.args[0]
    assert checked_result["summary"] == "마스킹:요약 원문"


@patch("models.consult.nodes.self_check_node.self_check")
@patch("models.consult.nodes.strategy.call_llm")
@patch("models.consult.nodes.suggested_chips.call_llm")
@patch("models.consult.nodes.question_analysis.call_llm")
@patch("models.consult.nodes.trend_for_consult.get_trend", return_value=None)
@patch("models.consult.nodes.market_for_consult.get_market", return_value=None)
def test_self_check_reject_retries_strategy_once_then_returns_error(
    _mock_get_market,
    _mock_get_trend,
    mock_question_call_llm,
    mock_chips_call_llm,
    mock_strategy_call_llm,
    mock_self_check,
) -> None:
    mock_question_call_llm.return_value = (
        json.dumps(
            {
                "rewritten_question": "우리 카페 홍보 전략",
                "is_sufficient": True,
                "missing_info": [],
                "keyword": None,
            }
        ),
        10,
    )
    mock_chips_call_llm.return_value = (
        json.dumps({"chips": ["질문 1", "질문 2", "질문 3"]}),
        10,
    )
    mock_strategy_call_llm.return_value = (
        json.dumps(
            {
                "title": "전략 제목",
                "summary": "요약",
                "actions": [{"type": "promotion", "content": "액션"}],
                "reasons": ["근거"],
            }
        ),
        10,
    )
    mock_self_check.return_value = {
        "action": "reject",
        "reasons": ["답변 근거 없음"],
        "message": "답변 근거가 부족합니다.",
    }

    result = build_consultant().invoke(_initial_state())

    assert mock_strategy_call_llm.call_count == 2
    assert mock_self_check.call_count == 2
    assert result["status"] == "error"
    assert result["issues"][-1]["reason"] == "unknown"


def test_default_path_skips_link_to_ads() -> None:
    """link_to_ads는 사용자가 버튼을 눌렀을 때만 호출돼야 하므로 기본 경로에 없어야 한다."""
    drawable = build_consultant().get_graph()

    assert "link_to_ads" not in drawable.nodes

    edges = {(edge.source, edge.target) for edge in drawable.edges}
    assert ("strategy_check", "security_output") in edges
    assert ("strategy_check", "link_to_ads") not in edges


def test_validation_routers_follow_contract_actions() -> None:
    graph_module = import_module("models.consult.graph.build_consultant")
    route_input = getattr(graph_module, "route_after_security_input", None)
    route_output = getattr(graph_module, "route_after_security_output", None)
    route_self_check = getattr(graph_module, "route_after_self_check", None)

    assert route_input is not None
    assert route_output is not None
    assert route_self_check is not None

    assert route_input({"status": "blocked"}) == "end"
    assert route_input({}) == "question_analysis"
    assert route_output({"status": "blocked"}) == "end"
    assert route_output({}) == "self_check_node"
    assert route_self_check({"status": "error"}) == "end"
    assert route_self_check(
        {"validation": {"self_check": {"action": "reject"}}}
    ) == "strategy"
    assert route_self_check(
        {"validation": {"self_check": {"action": "pass"}}}
    ) == "end"


def test_default_path_has_expected_topology() -> None:
    """SDP §6.1 순서대로 연결돼 있어야 한다. market_for_consult·trend_for_consult는
    서로의 결과를 쓰지 않아(v2 섹션F) suggested_chips에서 갈라졌다가 strategy 앞에서
    합류하는 병렬 구간이고, 나머지는 순차 연결이다."""
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
        ("security_input", "__end__"),
        ("question_analysis", "suggested_chips"),
        ("suggested_chips", "market_for_consult"),
        ("suggested_chips", "trend_for_consult"),
        ("market_for_consult", "strategy"),
        ("trend_for_consult", "strategy"),
        ("strategy", "strategy_check"),
        ("strategy_check", "security_output"),
        ("security_output", "self_check_node"),
        ("security_output", "__end__"),
        ("self_check_node", "strategy"),
        ("self_check_node", "__end__"),
    }
