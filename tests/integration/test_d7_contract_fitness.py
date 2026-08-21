"""
tests/integration/test_d7_contract_fitness.py
— D7 서비스↔모델 계약 적합성 검사

★ 관리: 전민재 PM  (D-295 · D-309)
  아래 MODEL_READS_* 상수는 `models/basic/main.py::_build_initial_state` 가
  실제로 읽는 키 목록이다. 모델 쪽을 고치면 이 상수도 함께 고쳐야 하는데,
  서비스 개발 담당은 모델 내부를 모르므로 갱신할 수 없다.
  → 모델 내부 지식이 필요한 테스트는 모델을 관리한 쪽이 관리한다.

  같은 디렉터리의 `test_d7_model_boundary.py` 는 반대다 — run() 만 호출하고
  모델 내부를 전혀 모르므로 서비스 개발 담당이 관리한다.

★ 무엇을 잡는가
  PR #103(서비스)과 PR #147(모델)은 각자 내부적으로는 옳지만, 두 계약이
  맞물리는 지점에서 어긋난다. 그 지점을 D7 통합 당일이 아니라 지금 드러낸다.
  대표 사례가 source_gen_id(모델) vs source_context(서비스) 불일치다(D-306).

★ 비용 0원 · LLM 호출 0회
  실제 그래프를 돌리지 않는다. "모델이 낼 수 있는 응답 모양"을 서비스 Pydantic
  스키마에 직접 넣어볼 뿐이라 CI 에서 매 PR 마다 돌려도 부담이 없다.

★ 이 파일을 고쳐야 하는 순간
  `models/basic/main.py` 또는 `models/shared/state_common.py` 의 입력 키가 바뀔 때.
  반드시 그 수정과 **같은 PR** 에 넣는다(D-266) — 테스트만 먼저 커밋하면
  CI 가 빨간불이 되어 main 병합이 막힌다.

실행:
    uv run --locked --all-groups pytest tests/integration/test_d7_contract_fitness.py -q
"""

from __future__ import annotations

import pytest

# ─────────────────────────────────────────────────────────────────────────────
# 0. 전제 확인 — D4 계약(PR #103)이 병합돼 있어야 한다
#    ConsultantSourceContext 는 PR #103 에서 신설된 심볼이다. 미병합 브랜치에서는
#    ImportError 로 수집 자체가 실패한다. 그러면 "내 환경 문제인가"로 시간을 쓴다.
#    → 이유를 밝히고 skip 한다. skip 이 보이면 그 자체가 D7 차단 신호다(D-294).
# ─────────────────────────────────────────────────────────────────────────────
try:
    from backend.schemas import (
        BasicModelResult,
        BlockedResult,
        ConsultantModelResult,
        ConsultantSourceContext,
        ErrorResult,
        ModelRequest,
    )

    _SCHEMA_READY, _SCHEMA_ERROR = True, ""
except ImportError as exc:  # pragma: no cover - 브랜치 상태에 따른 방어
    _SCHEMA_READY, _SCHEMA_ERROR = False, str(exc)

pytestmark = pytest.mark.skipif(
    not _SCHEMA_READY,
    reason=(
        "backend.schemas 에 D4 계약이 없다. PR #103 이 병합됐는지 확인하라. "
        f"({_SCHEMA_ERROR})"
    ),
)

# ─────────────────────────────────────────────────────────────────────────────
# 공용 픽스처 데이터
# ─────────────────────────────────────────────────────────────────────────────
STORE = {
    "name": "카페 코드잇",
    "type": "카페",
    "address": "서울 강남구 역삼동",
    "lat": 37.5,
    "lng": 127.0,
}

SOURCE_CONTEXT = {
    "generation_id": 7,
    "strategy": {
        "summary": "점심 시간대 직장인을 겨냥한 세트 메뉴 도입",
        "actions": [
            {"type": "menu", "content": "런치 세트 2종 출시"},
            {"type": "promotion", "content": "11~14시 10% 할인"},
        ],
    },
    "reasons": ["동일 상권 객단가 평균 대비 12% 낮음"],
    "sources": ["상권분석", "트렌드"],
}


def basic_request(**over) -> dict:
    """서비스가 기본 챗봇에 넘기는 ModelRequest 를 dict 로 만든다."""
    payload = {
        "chatbot_type": "basic",
        "user_id": 1,
        "question": "여름 신메뉴 홍보 문구 만들어줘",
        "platform": "instagram",
        "store": STORE,
    }
    payload.update(over)
    return ModelRequest.model_validate(payload).model_dump(mode="json")


def basic_ok(**over) -> dict:
    """기본 챗봇이 성공했을 때 내는 응답."""
    return {
        "status": "ok",
        "title": "여름 신메뉴",
        "proposals": [{"copy": "문구1"}, {"copy": "문구2"}, {"copy": "문구3"}],
        "sources": [],
        "tokens_used": 1200,
        "suggested_chips": [],
        **over,
    }


def consult_ok(**over) -> dict:
    """컨설턴트가 성공했을 때 내는 응답."""
    return {
        "status": "ok",
        "title": "여름 성수기 전략",
        "strategy": {
            "summary": "점심 시간대 직장인을 겨냥한 세트 메뉴 도입",
            "actions": [{"type": "target", "content": "직장인 메시지 강화"}],
        },
        "reasons": ["동일 상권 객단가 평균 대비 12% 낮음"],
        "sources": ["상권분석"],
        "tokens_used": 2400,
        "suggested_chips": ["메뉴는?", "가격은?", "홍보는?"],
        **over,
    }


# ═════════════════════════════════════════════════════════════════════════════
# 1. 요청 방향 — 서비스가 보내는 키와 모델이 읽는 키가 같은가
# ═════════════════════════════════════════════════════════════════════════════
# ★ models/basic/main.py::_build_initial_state 가 읽는 키를 손으로 선언한다.
#   두 팀의 명시적 합의 지점이며, 모델 쪽을 고치면 여기도 함께 고친다.
MODEL_READS_REQUIRED = frozenset(
    {"chatbot_type", "user_id", "question", "platform", "store"}
)
MODEL_READS_OPTIONAL = frozenset({"extra", "source_context"})


def test_model_request_supplies_every_key_the_model_requires():
    """모델이 필수로 읽는 키를 서비스가 전부 보내는가."""
    payload = basic_request()
    missing = MODEL_READS_REQUIRED - payload.keys()
    assert not missing, (
        f"모델이 읽는데 서비스가 보내지 않는 키: {sorted(missing)}\n"
        "→ ModelRequest 에 필드를 추가하거나 모델이 그 키를 읽지 않도록 고친다."
    )


def test_no_key_is_silently_dropped_between_service_and_model():
    """서비스가 보내는데 모델이 읽지 않는 키가 있으면 조용히 버려진다.

    ★ source_gen_id(모델) vs source_context(서비스) 불일치를 잡는 테스트다(D-306).
      이 테스트가 빨간불인 동안 컨설팅→광고 연계는 전략 데이터를 통째로 잃는다.
      서비스는 공개 요청의 source_gen_id 를 서버가 관리권·타입·상태로 검증한 뒤
      전략 원문으로 치환해 보낸다 — 프론트엔드가 남의 generation_id 를 주입할 수
      없으므로 서비스 쪽이 정답이고, 모델이 여기에 맞춘다.
    """
    payload = basic_request(source_context=SOURCE_CONTEXT)
    unread = payload.keys() - (MODEL_READS_REQUIRED | MODEL_READS_OPTIONAL)
    assert not unread, (
        f"서비스가 보내는데 모델이 읽지 않는 키: {sorted(unread)}\n"
        "→ models/basic/main.py::_build_initial_state 에 해당 키를 추가한다(D-306)."
    )


def test_source_context_fixture_matches_service_schema():
    """이 파일의 SOURCE_CONTEXT 픽스처가 실제 서비스 계약과 같은 모양인가.

    픽스처가 계약에서 벗어나면 이 파일의 나머지 검사가 전부 헛돈다.
    """
    ConsultantSourceContext.model_validate(SOURCE_CONTEXT)


def test_store_serializes_to_plain_dict():
    """StoreContext 는 dict 로 직렬화돼야 모델의 StoreInfo TypedDict 와 맞는다."""
    store = basic_request()["store"]
    assert isinstance(store, dict)
    assert set(store) == {"name", "type", "address", "lat", "lng"}


def test_extra_is_none_when_not_supplied():
    """extra 미지정 시 None 이 온다 — 모델은 `request.get("extra") or {}` 로 받는다."""
    assert basic_request()["extra"] is None


def test_source_context_actions_are_objects_not_strings():
    """★ actions 는 문자열 배열이 아니라 {type, content} 객체 배열이다.

    모델에서 그대로 join 하면 TypeError 가 난다. copy_gen 이 이 모양을 알아야 한다.
    """
    actions = basic_request(source_context=SOURCE_CONTEXT)["source_context"]["strategy"][
        "actions"
    ]
    assert all(isinstance(a, dict) for a in actions)
    assert {"type", "content"} <= set(actions[0])


def test_consultant_request_never_carries_source_context():
    """컨설턴트는 연계 Context 를 받지 않는다.

    서비스가 chatbot_type != "basic" 이면 SourceGenerationConflict(409)로 막는다.
    모델 쪽에서 컨설턴트 파이프라인에 source_context 처리를 넣을 필요가 없다.
    """
    payload = ModelRequest.model_validate(
        {
            "chatbot_type": "consultant",
            "user_id": 1,
            "question": "여름철 객단가를 올리려면?",
            "store": STORE,
        }
    ).model_dump(mode="json")
    assert payload["platform"] is None
    assert payload["source_context"] is None


# ═════════════════════════════════════════════════════════════════════════════
# 2. 응답 방향 — 기본 챗봇
# ═════════════════════════════════════════════════════════════════════════════
def test_basic_happy_path():
    BasicModelResult.model_validate(basic_ok())


def test_basic_allows_empty_sources():
    """Basic 은 sources 최소 개수가 없다 — main.py 의 `or []` 폴백이 안전하다(D-284)."""
    BasicModelResult.model_validate(basic_ok(sources=[]))


@pytest.mark.parametrize(
    "payload,why",
    [
        (basic_ok(suggested_chips=["질문1"]), "Basic 의 suggested_chips 는 반드시 빈 배열"),
        (basic_ok(proposals=[{"copy": "a"}, {"copy": "b"}]), "proposals 는 정확히 3개(D-018)"),
        (basic_ok(title=""), "title 은 비어 있을 수 없다 — channel_format 폴백 필요(D-213)"),
        (basic_ok(tokens_used=-1), "tokens_used 는 음수일 수 없다"),
    ],
)
def test_basic_contract_violations_are_rejected(payload, why):
    with pytest.raises(Exception, match=r".*"):
        BasicModelResult.model_validate(payload)


def test_regulation_blocked_slot_matches_proposal_invariant():
    """검증 함수 계약서 §8.2 규제 노드가 만드는 차단 슬롯이 계약과 맞는가."""
    blocked_slot = {
        "copy": None,
        "image_b64": None,
        "error": {"field": "copy", "reason": "content_policy", "message": "부당광고 위험"},
    }
    BasicModelResult.model_validate(
        basic_ok(proposals=[{"copy": "a"}, {"copy": "b"}, blocked_slot])
    )


def test_blocked_slot_must_null_out_copy():
    """차단 슬롯에 copy 를 남기면 서비스에서 검증 실패한다."""
    bad = {
        "copy": "남은 문구",
        "image_b64": None,
        "error": {"field": "copy", "reason": "content_policy", "message": "x"},
    }
    with pytest.raises(Exception, match=r".*"):
        BasicModelResult.model_validate(
            basic_ok(proposals=[{"copy": "a"}, {"copy": "b"}, bad])
        )


def test_image_failure_slot_keeps_copy_only():
    """이미지만 실패한 슬롯은 copy 를 유지한다 — 부분 성공(D-018)."""
    slot = {
        "copy": "문구는 성공",
        "image_b64": None,
        "error": {"field": "image", "reason": "timeout", "message": "이미지 생성 실패"},
    }
    BasicModelResult.model_validate(basic_ok(proposals=[{"copy": "a"}, {"copy": "b"}, slot]))


# ═════════════════════════════════════════════════════════════════════════════
# 3. 응답 방향 — 컨설턴트
#    ★ Basic 과 달리 최소 개수 제약이 여럿이다. `or []` 폴백을 복사하면 깨진다(D-310).
# ═════════════════════════════════════════════════════════════════════════════
def test_consultant_happy_path():
    ConsultantModelResult.model_validate(consult_ok())


@pytest.mark.parametrize(
    "payload,why",
    [
        (consult_ok(sources=[]), "Consultant 의 sources 는 최소 1개"),
        (consult_ok(reasons=[]), "reasons 는 최소 1개"),
        (consult_ok(suggested_chips=["a", "b"]), "suggested_chips 는 정확히 3개"),
        (consult_ok(suggested_chips=["a", "b", "c", "d"]), "suggested_chips 는 정확히 3개"),
        (consult_ok(title=""), "title 은 비어 있을 수 없다"),
    ],
)
def test_consultant_minimums_are_enforced(payload, why):
    with pytest.raises(Exception, match=r".*"):
        ConsultantModelResult.model_validate(payload)


def _strategy_with(action_count: int) -> dict:
    return {
        "summary": "요약",
        "actions": [{"type": "other", "content": f"실행 {i}"} for i in range(action_count)],
    }


@pytest.mark.parametrize("count", [0, 4, 5])
def test_consultant_actions_outside_one_to_three_are_rejected(count):
    """★ actions_wrong_length 의 정체 — 계약상 actions 는 1~3개다(D-308).

    backend/schemas.py 의 ConsultantStrategy 가 단일 소스다.
    컨설턴트 프롬프트·평가 스크립트가 다른 숫자를 쓰고 있으면 여기서 갈린다.
    """
    with pytest.raises(Exception, match=r".*"):
        ConsultantModelResult.model_validate(consult_ok(strategy=_strategy_with(count)))


@pytest.mark.parametrize("count", [1, 2, 3])
def test_consultant_actions_one_to_three_are_accepted(count):
    ConsultantModelResult.model_validate(consult_ok(strategy=_strategy_with(count)))


# ═════════════════════════════════════════════════════════════════════════════
# 4. 차단·오류 응답 — 두 챗봇 공통
# ═════════════════════════════════════════════════════════════════════════════
@pytest.mark.parametrize("action", ["block", "reask", "warn"])
def test_blocked_result_accepts_contract_actions(action):
    BlockedResult.model_validate(
        {
            "status": "blocked",
            "action": action,
            "reason": "illegal_or_injection",
            "message": "요청을 처리할 수 없습니다.",
        }
    )


@pytest.mark.parametrize(
    "bad,why",
    [
        ({"status": "blocked", "action": "reject", "reason": "x", "message": "y"},
         "self_check 의 reject 는 blocked action 이 아니다(P-038)"),
        ({"status": "blocked", "action": None, "reason": "x", "message": "y"},
         "action 이 None 이면 502 — D-285 폴백이 필요한 이유"),
        ({"status": "blocked", "action": "block", "reason": "", "message": "y"},
         "reason 은 비어 있을 수 없다"),
        ({"status": "blocked", "action": "block", "reason": "x", "message": ""},
         "message 는 비어 있을 수 없다(D-215)"),
    ],
)
def test_blocked_result_rejects_contract_violations(bad, why):
    with pytest.raises(Exception, match=r".*"):
        BlockedResult.model_validate(bad)


@pytest.mark.parametrize("reason", ["timeout", "rate_limit", "provider_error", "unknown"])
def test_error_result_accepts_only_four_reasons(reason):
    ErrorResult.model_validate(
        {"status": "error", "reason": reason, "message": "모델 처리 중 오류가 발생했습니다."}
    )


def test_error_result_rejects_internal_reason_names():
    """모델 내부 reason 을 그대로 올리면 502 가 난다 — main.py 가 매핑한다(D-214·D-286)."""
    for internal in ("copy_generation_failed", "self_check_failed", "regulation_risk"):
        with pytest.raises(Exception, match=r".*"):
            ErrorResult.model_validate(
                {"status": "error", "reason": internal, "message": "x"}
            )


# ═════════════════════════════════════════════════════════════════════════════
# 5. 교차 검증 — 모델 모듈을 import 할 수 있을 때만 (2차 안전망)
#    §1 의 MODEL_READS_* 는 손으로 유지하는 '선언'이라 갱신을 잊을 수 있다.
#    모델 모듈이 import 되는 환경에서는 실제 동작으로 한 번 더 확인한다.
#    LangGraph 미설치 등으로 import 가 안 되면 조용히 건너뛴다.
# ═════════════════════════════════════════════════════════════════════════════
def _model_main():
    return pytest.importorskip(
        "models.basic.main",
        reason="모델 모듈을 import 할 수 없는 환경 — §1 선언 기반 검사로 충분하다",
    )


def test_declared_required_keys_match_model_implementation():
    """MODEL_READS_REQUIRED 선언이 main.py 의 실제 필수 키와 일치하는가."""
    main = _model_main()
    assert frozenset(main._REQUIRED_KEYS) == MODEL_READS_REQUIRED, (
        "§1 의 MODEL_READS_REQUIRED 선언과 models/basic/main.py::_REQUIRED_KEYS 가 다르다.\n"
        "→ 모델을 고쳤다면 이 파일의 선언도 같은 PR 에서 고친다(D-266)."
    )


def test_source_context_actually_reaches_the_graph_state():
    """서비스가 보낸 source_context 가 그래프 state 까지 도달하는가(D-306).

    §1 은 '키 이름이 맞는가'만 보고, 여기서는 '값이 실제로 전달되는가'를 본다.
    """
    main = _model_main()
    payload = basic_request(source_context=SOURCE_CONTEXT)
    state = main._build_initial_state(payload)

    assert state.get("source_context") == SOURCE_CONTEXT, (
        "source_context 가 그래프 state 에 전달되지 않는다.\n"
        "→ _build_initial_state 에 `\"source_context\": request.get(\"source_context\")` 를 넣는다."
    )
    assert "source_gen_id" not in state, (
        "state 에 source_gen_id 가 남아 있다 — 서비스는 이 키를 보내지 않으므로 항상 None 이다."
    )


def test_deadline_is_set_and_shorter_than_service_timeout():
    """D-291·D-307 — 모델 자체 예산이 서비스 타임아웃보다 짧아야 한다.

    asyncio.wait_for 는 to_thread 스레드를 취소하지 못하므로, 실제로 작업을
    멈추는 것은 모델 내부 deadline 뿐이다.
    """
    main = _model_main()
    from models.shared.config import LLM_DEADLINE_SECONDS

    state = main._build_initial_state(basic_request())
    assert isinstance(state.get("deadline"), float) and state["deadline"] > 0
    assert LLM_DEADLINE_SECONDS < 60, (
        f"LLM_DEADLINE_SECONDS={LLM_DEADLINE_SECONDS} 가 서비스 최소 타임아웃(60초) 이상이다.\n"
        "→ 모델이 스스로 멈추지 못하면 좀비 스레드가 토큰을 계속 쓴다(D-307)."
    )
