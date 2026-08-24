# models/consult/nodes/strategy.py 테스트 (D4 섹션 1~5: 전략 생성 + 상권 데이터 주입 + actions 구조화 + 근거 재생성)
import json
from unittest.mock import patch

import httpx
import openai
import pytest

from models.consult.nodes.strategy import strategy
from models.consult.prompts.strategy import RETRY_REASONS_HINT

_STORE = {
    "name": "카페 코드잇",
    "type": "카페",
    "address": "서울 강남구 역삼동",
    "lat": 37.5,
    "lng": 127.0,
}


_MARKET = {
    "total_count": 43,
    "same_industry_count": 12,
    "nearest_distance_m": 55,
    "density_tier": "높음",
    "industry_breakdown": {"카페": 12, "편의점": 5},
}

_ACTIONS = [
    {"type": "promotion", "content": "선착순 20명 할인으로 신규 유입을 만드세요"},
    {"type": "menu", "content": "대표 메뉴를 시즌 한정 구성으로 앞세우세요"},
]

_REASONS = [
    "반경 내 동일 업종이 12곳으로 밀도 등급이 '높음'입니다",
    "선착순 할인은 즉각적인 신규 유입 효과가 있습니다",
]

_TREND = {
    "keyword": "아이스아메리카노",
    "direction": "상승",
    "related": ["냉커피", "여름음료"],
    "weather": None,
}


def _state(
    question: str = "우리 카페 어떻게 홍보하면 좋을까요?",
    market: dict | None = None,
    trend: dict | None = None,
    tokens_used: int = 0,
    sources: list[str] | None = None,
) -> dict:
    state = {
        "chatbot_type": "consultant",
        "user_id": 1,
        "question": question,
        "store": _STORE,
        "context": {"market": market, "trend": trend},
        "tokens_used": tokens_used,
    }
    if sources is not None:
        state["sources"] = sources
    return state


def _state_without_context(question: str = "우리 카페 어떻게 홍보하면 좋을까요?") -> dict:
    return {
        "chatbot_type": "consultant",
        "user_id": 1,
        "question": question,
        "store": _STORE,
    }


def _payload(summary: str = "전략 요약", actions=None, reasons=None, title="전략 제목") -> dict:
    payload = {
        "summary": summary,
        "actions": _ACTIONS if actions is None else actions,
        "reasons": _REASONS if reasons is None else reasons,
    }
    if title is not _OMIT:
        payload["title"] = title
    return payload


_OMIT = object()


def _response(payload, tokens: int = 100) -> tuple[str, int]:
    text = json.dumps(payload, ensure_ascii=False) if not isinstance(payload, str) else payload
    return text, tokens


@patch("models.consult.nodes.strategy.call_llm")
def test_returns_summary_actions_and_reasons_from_llm(mock_call_llm) -> None:
    mock_call_llm.return_value = _response(_payload("시즌 한정 메뉴로 신규 고객을 유입하세요."))

    result = strategy(_state())

    assert result == {
        "result": {
            "title": "전략 제목",
            "summary": "시즌 한정 메뉴로 신규 고객을 유입하세요.",
            "actions": _ACTIONS,
            "reasons": _REASONS,
        },
        "tokens_used": 100,
        "retry_count": 0,
        "sources": ["가게정보"],
    }


@pytest.mark.parametrize("invalid_title", [_OMIT, None, "", "   ", 123, ["제목"]])
@patch("models.consult.nodes.strategy.call_llm")
def test_falls_back_to_default_title_when_missing_or_invalid(mock_call_llm, invalid_title) -> None:
    """title은 summary/actions/reasons와 달리 형식 오류로 전체 응답을 실패시키지 않는다
    — 제목 하나 때문에 좋은 전략을 버리면 안 된다(PM 리뷰, D7 계약 정합성).
    가게 이름 기반 기본 제목으로 폴백한다(mock_chatbot.py와 동일 패턴)."""
    mock_call_llm.return_value = _response(_payload(title=invalid_title))

    result = strategy(_state())

    assert result["result"]["title"] == "카페 코드잇 마케팅 전략"


@patch("models.consult.nodes.strategy.call_llm")
def test_accumulates_retry_count_onto_existing_state_value(mock_call_llm) -> None:
    """retry_count는 strategy 혼자만 쓰는 게 아니라 앞으로 다른 노드(D9 strategy_check)도
    같은 키에 쓸 예정이라, 덮어쓰지 않고 기존 값에 더한다(PM 리뷰, PR #93)."""
    mock_call_llm.side_effect = [
        _response(_payload(reasons=[])),  # 1차: 근거 없음 → strategy 내부에서 1회 재시도
        _response(_payload(reasons=_REASONS)),  # 2차: 성공
    ]
    state = _state()
    state["retry_count"] = 3  # 다른 노드가 이미 채워둔 값을 흉내

    result = strategy(state)

    assert result["retry_count"] == 3 + 1


@patch("models.consult.nodes.strategy.call_llm")
def test_requests_json_mode(mock_call_llm) -> None:
    mock_call_llm.return_value = _response(_payload())

    strategy(_state())

    assert mock_call_llm.call_args.kwargs.get("json_mode") is True


@patch("models.consult.nodes.strategy.call_llm")
def test_passes_deadline_from_state_to_call_llm(mock_call_llm) -> None:
    """security_input이 세팅한 state["deadline"]을 그대로 call_llm에 넘긴다(PM 리뷰, PR #93)."""
    mock_call_llm.return_value = _response(_payload())
    state = _state()
    state["deadline"] = 1234.5

    strategy(state)

    assert mock_call_llm.call_args.kwargs.get("deadline") == 1234.5


@patch("models.consult.nodes.strategy.call_llm")
def test_reuses_same_deadline_across_retries(mock_call_llm) -> None:
    """근거 재생성으로 call_llm을 여러 번 불러도, 매번 새 예산을 받는 게 아니라
    그래프 진입 시 세팅된 동일한 deadline을 계속 공유한다(PM 리뷰, PR #93)."""
    mock_call_llm.side_effect = [
        _response(_payload(reasons=[])),
        _response(_payload(reasons=_REASONS)),
    ]
    state = _state()
    state["deadline"] = 1234.5

    strategy(state)

    first_deadline = mock_call_llm.call_args_list[0].kwargs.get("deadline")
    second_deadline = mock_call_llm.call_args_list[1].kwargs.get("deadline")
    assert first_deadline == 1234.5
    assert second_deadline == 1234.5


@patch("models.consult.nodes.strategy.call_llm")
def test_accumulates_tokens_used(mock_call_llm) -> None:
    mock_call_llm.return_value = _response(_payload(), tokens=150)

    result = strategy(_state(tokens_used=50))

    assert result["tokens_used"] == 200


@patch("models.consult.nodes.strategy.call_llm")
def test_strips_leading_and_trailing_whitespace_from_summary(mock_call_llm) -> None:
    mock_call_llm.return_value = _response(_payload("  전략 내용\n"))

    result = strategy(_state())

    assert result["result"]["summary"] == "전략 내용"


@patch("models.consult.nodes.strategy.call_llm")
def test_strips_whitespace_from_action_content(mock_call_llm) -> None:
    mock_call_llm.return_value = _response(
        _payload(actions=[{"type": "menu", "content": "  공백 포함 항목\n"}])
    )

    result = strategy(_state())

    assert result["result"]["actions"] == [{"type": "menu", "content": "공백 포함 항목"}]


@patch("models.consult.nodes.strategy.call_llm")
def test_strips_whitespace_from_reasons(mock_call_llm) -> None:
    mock_call_llm.return_value = _response(_payload(reasons=["  공백 포함 근거\n"]))

    result = strategy(_state())

    assert result["result"]["reasons"] == ["공백 포함 근거"]


@patch("models.consult.nodes.strategy.call_llm")
def test_passes_question_and_store_info_to_prompt(mock_call_llm) -> None:
    mock_call_llm.return_value = _response(_payload())

    strategy(_state("우리 카페 어떻게 홍보하면 좋을까요?"))

    system_prompt, user_prompt = mock_call_llm.call_args.args
    assert "우리 카페 어떻게 홍보하면 좋을까요?" in user_prompt
    assert "카페 코드잇" in user_prompt
    assert "카페" in user_prompt
    assert "마케팅 컨설턴트" in system_prompt


@patch("models.consult.nodes.strategy.call_llm")
def test_includes_market_data_when_available(mock_call_llm) -> None:
    mock_call_llm.return_value = _response(_payload())

    strategy(_state(market=_MARKET))

    _, user_prompt = mock_call_llm.call_args.args
    assert "43" in user_prompt
    assert "12" in user_prompt
    assert "55" in user_prompt
    assert "높음" in user_prompt
    # industry_breakdown("업종 분포")은 프롬프트에서 뺀다 — 원본이 API 페이지 상한
    # (1000곳)을 넘는 지역은 부분집합만 반영돼 부정확한 근거가 될 수 있다(PM 리뷰).
    assert "편의점" not in user_prompt


@patch("models.consult.nodes.strategy.call_llm")
def test_omits_market_section_when_market_is_none(mock_call_llm) -> None:
    mock_call_llm.return_value = _response(_payload())

    strategy(_state(market=None))

    _, user_prompt = mock_call_llm.call_args.args
    assert "상권 데이터" not in user_prompt


@patch("models.consult.nodes.strategy.call_llm")
def test_omits_market_section_when_context_missing_entirely(mock_call_llm) -> None:
    """market_for_consult가 아직 안 돈 상태(그래프 조기 실행 등)에서도 죽지 않는다."""
    mock_call_llm.return_value = _response(_payload())

    strategy(_state_without_context())

    _, user_prompt = mock_call_llm.call_args.args
    assert "상권 데이터" not in user_prompt


@patch("models.consult.nodes.strategy.call_llm")
def test_includes_trend_data_when_available(mock_call_llm) -> None:
    mock_call_llm.return_value = _response(_payload())

    strategy(_state(trend=_TREND))

    _, user_prompt = mock_call_llm.call_args.args
    assert "트렌드 데이터" in user_prompt
    assert "상승" in user_prompt
    assert "냉커피" in user_prompt
    assert "여름음료" in user_prompt


@patch("models.consult.nodes.strategy.call_llm")
def test_omits_trend_section_when_trend_is_none(mock_call_llm) -> None:
    mock_call_llm.return_value = _response(_payload())

    strategy(_state(trend=None))

    _, user_prompt = mock_call_llm.call_args.args
    assert "트렌드 데이터" not in user_prompt


@patch("models.consult.nodes.strategy.call_llm")
def test_omits_trend_section_when_context_missing_entirely(mock_call_llm) -> None:
    mock_call_llm.return_value = _response(_payload())

    strategy(_state_without_context())

    _, user_prompt = mock_call_llm.call_args.args
    assert "트렌드 데이터" not in user_prompt


@patch("models.consult.nodes.strategy.call_llm")
def test_trend_section_includes_keyword(mock_call_llm) -> None:
    """direction만 있으면 "무엇의" 추이인지 LLM이 알 수 없다 — 조회 keyword 자체도
    프롬프트에 노출해야 한다."""
    mock_call_llm.return_value = _response(_payload())

    strategy(_state(trend=_TREND))

    _, user_prompt = mock_call_llm.call_args.args
    assert "아이스아메리카노" in user_prompt


@pytest.mark.parametrize("malformed_keyword", ["", "   ", 123, None])
@patch("models.consult.nodes.strategy.call_llm")
def test_trend_section_formats_malformed_keyword_as_no_info(mock_call_llm, malformed_keyword) -> None:
    """keyword가 빈 문자열·공백·숫자·None이면 그대로 프롬프트에 새지 않고 '정보 없음'으로
    안전하게 정규화된다."""
    mock_call_llm.return_value = _response(_payload())
    trend = {**_TREND, "keyword": malformed_keyword}

    strategy(_state(trend=trend))

    _, user_prompt = mock_call_llm.call_args.args
    assert "조회 검색어: 정보 없음" in user_prompt


@patch("models.consult.nodes.strategy.call_llm")
def test_includes_both_market_and_trend_data_when_both_available(mock_call_llm) -> None:
    mock_call_llm.return_value = _response(_payload())

    strategy(_state(market=_MARKET, trend=_TREND))

    _, user_prompt = mock_call_llm.call_args.args
    assert "상권 데이터" in user_prompt
    assert "트렌드 데이터" in user_prompt


@patch("models.consult.nodes.strategy.call_llm")
def test_adds_default_source_when_market_and_trend_both_unavailable(mock_call_llm) -> None:
    """market_for_consult·trend_for_consult가 둘 다 실패(또는 조기 실행)하면 sources가
    비어 있는 채로 넘어온다 — 서비스 계약(ConsultantModelResult.sources, min_length=1)이
    깨지므로, 최소한 가게 정보는 항상 근거로 쓰이니 "가게정보"를 기본 출처로 채운다."""
    mock_call_llm.return_value = _response(_payload())

    result = strategy(_state(market=None, trend=None))

    assert result["sources"] == ["가게정보"]


@patch("models.consult.nodes.strategy.call_llm")
def test_does_not_add_default_source_when_sources_already_accumulated(mock_call_llm) -> None:
    """market_for_consult·trend_for_consult 중 하나라도 성공해 이미 sources가 있으면
    "가게정보"를 덧붙이지 않는다(중복 방지 — operator.add reducer가 이 반환값을
    기존 sources에 그대로 더하므로, 여기서 빈 dict를 반환해야 늘어나지 않는다)."""
    mock_call_llm.return_value = _response(_payload())

    result = strategy(_state(market=_MARKET, sources=["상권분석"]))

    assert "sources" not in result


@patch("models.consult.nodes.strategy.call_llm")
def test_handles_none_nearest_distance_gracefully(mock_call_llm) -> None:
    """동일 업종이 0곳이면 nearest_distance_m이 None인데, 이 경우도 죽지 않고 포맷된다."""
    mock_call_llm.return_value = _response(_payload())
    market = {**_MARKET, "same_industry_count": 0, "nearest_distance_m": None, "density_tier": "경쟁 없음"}

    strategy(_state(market=market))

    _, user_prompt = mock_call_llm.call_args.args
    assert "상권 데이터" in user_prompt


@patch("models.consult.nodes.strategy.call_llm")
def test_handles_missing_market_fields_gracefully(mock_call_llm) -> None:
    """total_count/same_industry_count/density_tier가 누락돼도 KeyError 없이 '정보 없음'/'판단 불가'로 정규화한다."""
    mock_call_llm.return_value = _response(_payload())

    strategy(_state(market={"nearest_distance_m": 55}))

    _, user_prompt = mock_call_llm.call_args.args
    assert "상권 데이터" in user_prompt
    assert "정보 없음" in user_prompt
    assert "판단 불가" in user_prompt


@patch("models.consult.nodes.strategy.call_llm")
def test_formats_none_same_industry_count_as_no_info(mock_call_llm) -> None:
    """same_industry_count가 None이면 'None곳'이 아니라 '정보 없음'으로 표기한다."""
    mock_call_llm.return_value = _response(_payload())
    market = {**_MARKET, "same_industry_count": None}

    strategy(_state(market=market))

    _, user_prompt = mock_call_llm.call_args.args
    assert "None곳" not in user_prompt
    assert "정보 없음" in user_prompt


def test_system_prompt_includes_good_bad_example() -> None:
    """few-shot 예시(SDP §6.4 좋은/나쁜 전략)가 시스템 프롬프트에 포함돼 있다."""
    from models.consult.prompts.strategy import SYSTEM_PROMPT

    assert "나쁜" in SYSTEM_PROMPT
    assert "좋은" in SYSTEM_PROMPT


def test_system_prompt_requests_reasons() -> None:
    """reasons 필드와 "막연한 근거 불인정" 지시가 시스템 프롬프트에 포함돼 있다."""
    from models.consult.prompts.strategy import SYSTEM_PROMPT

    assert "reasons" in SYSTEM_PROMPT


@patch("models.consult.nodes.strategy.call_llm")
def test_propagates_call_llm_failure(mock_call_llm) -> None:
    """call_llm()이 재시도 끝에 예외를 던지면(완전 실패) 그대로 전파한다 — 질문 분석 노드와 동일 원칙."""
    request = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")
    response = httpx.Response(status_code=429, request=request)
    mock_call_llm.side_effect = openai.RateLimitError("rate limited", response=response, body=None)

    with pytest.raises(openai.RateLimitError):
        strategy(_state())


@patch("models.consult.nodes.strategy.call_llm")
def test_raises_when_response_is_not_json(mock_call_llm) -> None:
    mock_call_llm.return_value = _response("이건 JSON이 아님")

    with pytest.raises(ValueError):
        strategy(_state())


@pytest.mark.parametrize("blank_summary", ["", "   ", "\n\t"])
@patch("models.consult.nodes.strategy.call_llm")
def test_raises_when_summary_is_blank(mock_call_llm, blank_summary) -> None:
    """빈 문자열·공백뿐인 요약은 계약(title/summary 빈 문자열 불가)을 어기므로 명시적으로 실패시킨다."""
    mock_call_llm.return_value = _response(_payload(blank_summary))

    with pytest.raises(ValueError):
        strategy(_state())


@patch("models.consult.nodes.strategy.call_llm")
def test_raises_when_summary_field_missing(mock_call_llm) -> None:
    mock_call_llm.return_value = _response({"actions": _ACTIONS, "reasons": _REASONS})

    with pytest.raises(ValueError):
        strategy(_state())


@pytest.mark.parametrize(
    "invalid_actions",
    [
        [],  # 0개
        [{"type": "menu", "content": "a"}] * 4,  # 4개(3개 초과)
        "actions 아님",  # 리스트가 아님
        [{"type": "invalid_type", "content": "내용"}],  # enum 밖
        [{"type": ["menu"], "content": "내용"}],  # type이 리스트(해시 불가능 → TypeError 회귀 방지)
        [{"type": {"menu": True}, "content": "내용"}],  # type이 dict(해시 불가능 → TypeError 회귀 방지)
        [{"type": "menu"}],  # content 누락
        [{"type": "menu", "content": ""}],  # content 빈 문자열
        [{"type": "menu", "content": "   "}],  # content 공백뿐
        [{"content": "type 누락"}],  # type 누락
        ["문자열 항목"],  # 항목이 dict가 아님
    ],
)
@patch("models.consult.nodes.strategy.call_llm")
def test_raises_on_invalid_actions(mock_call_llm, invalid_actions) -> None:
    mock_call_llm.return_value = _response(_payload(actions=invalid_actions))

    with pytest.raises(ValueError):
        strategy(_state())


@pytest.mark.parametrize(
    "payload",
    [
        {"summary": "전략 요약", "actions": None, "reasons": _REASONS},  # actions가 명시적으로 None
        {"summary": "전략 요약", "reasons": _REASONS},  # actions 필드 자체가 없음
    ],
)
@patch("models.consult.nodes.strategy.call_llm")
def test_raises_when_actions_field_missing_or_null(mock_call_llm, payload) -> None:
    mock_call_llm.return_value = _response(payload)

    with pytest.raises(ValueError):
        strategy(_state())


@pytest.mark.parametrize("count", [1, 3])
@patch("models.consult.nodes.strategy.call_llm")
def test_accepts_actions_at_boundary_counts(mock_call_llm, count) -> None:
    """actions는 1개(최소)~3개(최대) 모두 허용한다."""
    actions = [{"type": "other", "content": f"항목 {i}"} for i in range(count)]
    mock_call_llm.return_value = _response(_payload(actions=actions))

    result = strategy(_state())

    assert result["result"]["actions"] == actions


# ── 섹션 5: 근거(reasons) 필수화 + 재생성 ─────────────────────────


@patch("models.consult.nodes.strategy.call_llm")
def test_retries_once_when_reasons_missing_then_succeeds(mock_call_llm) -> None:
    mock_call_llm.side_effect = [
        _response(_payload(reasons=[])),  # 1차: 근거 없음
        _response(_payload(reasons=_REASONS)),  # 2차: 근거 있음
    ]

    result = strategy(_state())

    assert mock_call_llm.call_count == 2
    assert result["result"]["reasons"] == _REASONS
    assert result["retry_count"] == 1


@patch("models.consult.nodes.strategy.call_llm")
def test_retry_prompt_includes_correction_hint(mock_call_llm) -> None:
    mock_call_llm.side_effect = [
        _response(_payload(reasons=[])),
        _response(_payload(reasons=_REASONS)),
    ]

    strategy(_state())

    first_call_user_prompt = mock_call_llm.call_args_list[0].args[1]
    second_call_user_prompt = mock_call_llm.call_args_list[1].args[1]
    assert RETRY_REASONS_HINT not in first_call_user_prompt
    assert RETRY_REASONS_HINT in second_call_user_prompt


@patch("models.consult.nodes.strategy.call_llm")
def test_accumulates_tokens_across_retries(mock_call_llm) -> None:
    mock_call_llm.side_effect = [
        _response(_payload(reasons=[]), tokens=100),
        _response(_payload(reasons=_REASONS), tokens=120),
    ]

    result = strategy(_state(tokens_used=10))

    assert result["tokens_used"] == 10 + 100 + 120


@patch("models.consult.nodes.strategy.call_llm")
def test_succeeds_on_second_retry_at_max_boundary(mock_call_llm) -> None:
    """1·2차 모두 근거 없음, 3차(2번째 재생성)에서 성공 — 재생성 상한 경계에서의 성공 케이스."""
    mock_call_llm.side_effect = [
        _response(_payload(reasons=[]), tokens=100),
        _response(_payload(reasons=[]), tokens=110),
        _response(_payload(reasons=_REASONS), tokens=120),
    ]

    result = strategy(_state(tokens_used=10))

    assert mock_call_llm.call_count == 3
    assert result["retry_count"] == 2
    assert result["result"]["reasons"] == _REASONS
    assert result["tokens_used"] == 10 + 100 + 110 + 120


@patch("models.consult.nodes.strategy.call_llm")
def test_raises_after_exhausting_reasons_retries(mock_call_llm) -> None:
    """근거 없는 응답이 3회(최초 1회+재생성 2회) 연속되면 예외를 던진다."""
    mock_call_llm.return_value = _response(_payload(reasons=[]))

    with pytest.raises(ValueError):
        strategy(_state())

    assert mock_call_llm.call_count == 3


@pytest.mark.parametrize(
    "invalid_reasons",
    [
        [],  # 빈 배열
        "reasons 아님",  # 리스트가 아님
        [""],  # 빈 문자열
        ["   "],  # 공백뿐
        [123],  # 문자열이 아닌 항목
    ],
)
@patch("models.consult.nodes.strategy.call_llm")
def test_treats_invalid_reasons_as_missing_and_retries(mock_call_llm, invalid_reasons) -> None:
    """형식이 안 맞는 reasons도 '근거 없음'과 동일하게 재생성 대상이다(예외가 아니라 재시도)."""
    mock_call_llm.side_effect = [
        _response(_payload(reasons=invalid_reasons)),
        _response(_payload(reasons=_REASONS)),
    ]

    result = strategy(_state())

    assert mock_call_llm.call_count == 2
    assert result["result"]["reasons"] == _REASONS


@patch("models.consult.nodes.strategy.call_llm")
def test_treats_null_reasons_as_missing_and_retries(mock_call_llm) -> None:
    """reasons 필드가 명시적으로 null이어도 '근거 없음'과 동일하게 재시도한다."""
    mock_call_llm.side_effect = [
        _response({"summary": "전략 요약", "actions": _ACTIONS, "reasons": None}),
        _response(_payload(reasons=_REASONS)),
    ]

    result = strategy(_state())

    assert mock_call_llm.call_count == 2
    assert result["result"]["reasons"] == _REASONS


@patch("models.consult.nodes.strategy.call_llm")
def test_reasons_field_missing_entirely_triggers_retry(mock_call_llm) -> None:
    mock_call_llm.side_effect = [
        _response({"summary": "전략 요약", "actions": _ACTIONS}),  # reasons 필드 자체가 없음
        _response(_payload()),
    ]

    result = strategy(_state())

    assert mock_call_llm.call_count == 2
    assert result["result"]["reasons"] == _REASONS


@patch("models.consult.nodes.strategy.call_llm")
def test_raises_immediately_on_malformed_actions_even_on_retry_attempt(mock_call_llm) -> None:
    """actions 형식 오류는 재생성 대상이 아니라 즉시 실패 — 근거 재생성 중이라도 예외로 처리한다."""
    mock_call_llm.side_effect = [
        _response(_payload(reasons=[])),  # 1차: 근거 없음 → 재시도 유발
        _response(_payload(actions=[])),  # 2차: actions 자체가 잘못됨 → 즉시 실패
    ]

    with pytest.raises(ValueError):
        strategy(_state())

    assert mock_call_llm.call_count == 2
