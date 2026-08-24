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
    캐싱된 환경에서는 조용히 성공해버려 이 테스트의 전제가 깨질 수 있다.

    suggested_chips·chips_fallback·tokens_used도 확인한다(Codex 리뷰) — 3-way
    병렬화(v3 섹션F)의 핵심 위험이 이 세 plain 필드(reducer 없음)의 병합이었는데,
    이전엔 병렬 시작 여부만 확인했지 병합 후 값이 실제로 보존되는지는 아무도
    검증하지 않았다."""
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
    # suggested_chips·chips_fallback은 suggested_chips 노드만 쓰는 필드라 market/trend와
    # 병렬로 묶여도 덮어써질 수 없다 — 실제로 병합 후에도 남아있는지 확인한다.
    assert result["suggested_chips"] == ["질문 1", "질문 2", "질문 3"]
    assert result["chips_fallback"] is False
    # question_analysis(100) + suggested_chips(50) + strategy(100) = 250.
    # market_for_consult·trend_for_consult는 LLM을 호출하지 않아 tokens_used를
    # 건드리지 않으므로, 3-way 병렬 묶음 안에서 tokens_used를 쓰는 노드는
    # suggested_chips 하나뿐이라 합계가 그대로 보존돼야 한다.
    assert result["tokens_used"] == 250


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
def test_suggested_chips_market_trend_run_in_parallel_not_sequential(
    mock_get_market,
    mock_get_trend,
    mock_question_call_llm,
    mock_chips_call_llm,
    mock_strategy_call_llm,
) -> None:
    """suggested_chips·market_for_consult·trend_for_consult 세 노드가 question_analysis
    직후 동시에 실행되는지 확인한다(v3 섹션F, 3-way 병렬화 — suggested_chips는 market/
    trend 결과를 쓰지 않아 더 이상 그 앞에서 순차로 기다릴 이유가 없다). 세 mock이
    threading.Barrier(3)에서 서로를 기다리게 한다 — 셋 중 하나라도 순차 실행이면
    나머지를 영원히 못 만나 타임아웃 예외를 던지고, 셋 다 병렬이면 거의 동시에
    도착해 정상 통과한다. 절대 시간 임계값에 의존하지 않아 느린 CI에서도 안정적이다
    (v2 섹션F Codex 리뷰 — 기존 sleep+임계값 비교는 느린 환경에서 flaky할 수 있다는
    지적과 동일 패턴)."""
    import threading

    barrier = threading.Barrier(3, timeout=2.0)

    def rendezvous_market(*args, **kwargs):
        barrier.wait()

    def rendezvous_trend(*args, **kwargs):
        barrier.wait()

    def rendezvous_chips(*args, **kwargs):
        barrier.wait()
        return (json.dumps({"chips": ["질문 1", "질문 2", "질문 3"]}), 50)

    mock_get_market.side_effect = rendezvous_market
    mock_get_trend.side_effect = rendezvous_trend
    mock_chips_call_llm.side_effect = rendezvous_chips
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
    mock_strategy_call_llm.return_value = (
        json.dumps({"summary": "요약", "actions": [{"type": "menu", "content": "액션"}], "reasons": ["근거"]}),
        100,
    )
    graph = build_consultant()

    # 순차 실행이면 barrier.wait()이 타임아웃돼 BrokenBarrierError가 여기서 전파된다.
    graph.invoke(_initial_state())

    mock_get_market.assert_called_once()
    mock_get_trend.assert_called_once()
    mock_chips_call_llm.assert_called_once()


def test_default_path_skips_link_to_ads() -> None:
    """link_to_ads는 사용자가 버튼을 눌렀을 때만 호출돼야 하므로 기본 경로에 없어야 한다."""
    drawable = build_consultant().get_graph()

    assert "link_to_ads" not in drawable.nodes

    edges = {(edge.source, edge.target) for edge in drawable.edges}
    assert ("strategy_check", "security_output") in edges
    assert ("strategy_check", "link_to_ads") not in edges


def test_default_path_has_expected_topology() -> None:
    """SDP §6.1 순서대로 연결돼 있어야 한다. suggested_chips·market_for_consult·
    trend_for_consult는 서로의 결과를 쓰지 않아(v3 섹션F) question_analysis 직후
    셋 다 갈라졌다가 strategy 앞에서 합류하는 병렬 구간이고, 나머지는 순차 연결이다."""
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
        ("question_analysis", "market_for_consult"),
        ("question_analysis", "trend_for_consult"),
        ("suggested_chips", "strategy"),
        ("market_for_consult", "strategy"),
        ("trend_for_consult", "strategy"),
        ("strategy", "strategy_check"),
        ("strategy_check", "security_output"),
        ("security_output", "self_check_node"),
        ("self_check_node", "__end__"),
    }
