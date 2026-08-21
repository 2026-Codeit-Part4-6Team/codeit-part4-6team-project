"""
models/basic/tests/test_main_contract.py
— run() / assemble_response() 서비스 계약 테스트 (D-210 필수 배치 · D-212 별도 작성)

★ 이 파일은 프로덕션 모듈을 건드리지 않는다 (D-292)
  이전 판은 models/basic/graph/build_basic.py 에 set_scenario() 라는
  테스트 전용 훅이 있어야 돌았다. 그 함수는 리뷰용 재현 스텁이었고 저장소에 없다.
  → 프로덕션에 테스트 훅을 심으면 브랜치마다 존재 여부가 갈려 테스트가 못 돈다.
  → 여기서는 monkeypatch 로 main 이 import 한 이름만 갈아끼운다.

★ 두 층으로 나눈다 (D-293)
  A. assemble_response() 직접 호출 — **그래프가 아예 필요 없다.**
     P0 4건이 전부 이 함수 안에 있으므로 계약 검증의 무게중심은 여기다.
     LangGraph·OpenAI·API 키 없이도, 어느 브랜치에서도 돈다.
  B. run() 진입점 — 가짜 그래프를 주입해 예외 미전파·필수 키·싱글턴·deadline 을 본다.

★ PR #147 원본이 뚫렸던 케이스를 각각 고정한다
  ① 정상 통과한 요청에 status 키가 없어 KeyError → 전 요청이 error
  ② sources 미설정 시 None → 서비스 Pydantic(list[str]) 502
  ③ blocked 인데 issues 가 비면 action·reason 이 None → 502
  ④ copy_generation_failed 를 unknown 으로 매핑 → D-073 위반
  ⑤ run() 이 예외를 던지지 않는다는 계약이 테스트되지 않음
"""

import pytest

from models.basic import main as main_mod
from models.basic.main import assemble_response, reset_graph, run

ERROR_REASONS = {"timeout", "rate_limit", "provider_error", "unknown"}
BLOCKED_ACTIONS = {"block", "reask", "warn"}

REQUEST = {
    "chatbot_type": "basic",
    "user_id": 1,
    "question": "여름 신메뉴 홍보 문구 만들어줘",
    "platform": "instagram",
    "store": {
        "name": "카페 코드잇",
        "type": "카페",
        "address": "서울 강남구 역삼동",
        "lat": 37.5,
        "lng": 127.0,
    },
}

# 검증 함수 계약서 §8 노드가 실제로 남기는 최종 state 모양.
# ★ pass 경로에서는 status 키를 세팅하지 않는다(§8.0-1 부분 업데이트만 반환).
STATE_OK = {
    "validation": {"input": {"action": "pass", "message": ""}},
    "result": {
        "title": "여름 신메뉴",
        "proposals": [{"copy": "a"}, {"copy": "b"}, {"copy": "c"}],
        "suggested_chips": [],
    },
    "tokens_used": 1234,
}
STATE_BLOCKED = {
    "status": "blocked",
    "issues": [
        {
            "source": "input",
            "action": "block",
            "reason": "illegal_or_injection",
            "message": "차단되었습니다.",
        }
    ],
}
STATE_BLOCKED_NO_ISSUE = {"status": "blocked"}  # 라우터가 status 만 세팅한 경우
STATE_ERROR = {
    "status": "error",
    "issues": [
        {
            "source": "copy_gen",
            "action": "reject",
            "reason": "copy_generation_failed",
            "message": "카피 생성 실패",
        }
    ],
}

_SCENARIOS = {
    "ok": STATE_OK,
    "blocked": STATE_BLOCKED,
    "blocked_no_issue": STATE_BLOCKED_NO_ISSUE,
    "error": STATE_ERROR,
}

SOURCE_CONTEXT = {
    "generation_id": 7,
    "strategy": {"summary": "점심 직장인 타깃",
                 "actions": [{"type": "menu", "content": "런치 세트 2종 출시"}]},
    "reasons": ["동일 상권 객단가 평균 대비 12% 낮음"],
    "sources": ["상권분석"],
}


# ═════════════════════════════════════════════════════════════════════════════
# A. assemble_response() — 그래프 의존성 0
#    여기가 계약 검증의 본체다. 실행에 LangGraph·OpenAI·API 키가 필요 없다.
# ═════════════════════════════════════════════════════════════════════════════
def test_state_without_status_is_ok_not_error():
    """① 가장 중요한 회귀.

    §8 노드는 pass 일 때 status 를 세팅하지 않으므로 정상 경로에는 키가 없다.
    state["status"] 로 읽으면 KeyError → 바깥 except 에 먹혀 전 요청이 error 로 나가고
    D-020 에 따라 크레딧까지 롤백된다. 서비스에 붙이는 순간 100% 재현된다.
    """
    r = assemble_response(dict(STATE_OK))
    assert r["status"] == "ok", f"정상 통과 상태가 {r['status']} 로 나갔다"
    assert r["title"] and len(r["proposals"]) == 3


def test_sources_is_list_never_none():
    """② sources 는 NotRequired 라 조회 노드가 안 돌면 키가 없다 → None 이면 502."""
    assert assemble_response(dict(STATE_OK))["sources"] == []


def test_sources_passthrough_when_present():
    r = assemble_response({**STATE_OK, "sources": ["상권분석", "트렌드"]})
    assert r["sources"] == ["상권분석", "트렌드"]


def test_ok_without_result_becomes_error():
    """result 가 비었는데 ok 로 나가면 서비스가 필수 필드 없는 응답을 받는다."""
    assert assemble_response({"status": "ok", "result": {}})["status"] == "error"


def test_ok_response_has_no_internal_keys():
    """state 내부 키가 서비스로 새지 않는다(D-212 '내부 키 누출')."""
    r = assemble_response(
        {
            **STATE_OK,
            "validation": {},
            "issues": [],
            "copy_retry_count": 1,
            "deadline": 123.4,
        }
    )
    leaked = {
        "validation",
        "issues",
        "copy_retry_count",
        "self_check_retry_count",
        "deadline",
        "ranked_copies",
    } & set(r)
    assert not leaked, f"내부 키 누출: {leaked}"


def test_result_status_key_cannot_override_ok():
    """result 안에 status 가 섞여도 최상위 ok 를 덮어쓰지 않는다."""
    state = {**STATE_OK, "result": {**STATE_OK["result"], "status": "generating"}}
    assert assemble_response(state)["status"] == "ok"


# ── blocked ─────────────────────────────────────────────────────────────────
def test_blocked_passes_through_issue():
    r = assemble_response(dict(STATE_BLOCKED))
    assert (r["status"], r["action"], r["reason"]) == (
        "blocked",
        "block",
        "illegal_or_injection",
    )
    assert r["message"]


def test_blocked_without_issues_still_satisfies_contract():
    """③ issues 를 채우지 않은 노드가 있어도 action·reason 이 None 으로 나가지 않는다.

    D-215 는 message 만 막았다. BlockedResult.action 은 enum, reason 은 필수라
    None 이면 D-073 과 같은 유형의 502 가 된다.
    """
    r = assemble_response(dict(STATE_BLOCKED_NO_ISSUE))
    assert r["action"] in BLOCKED_ACTIONS
    assert r["reason"] and isinstance(r["reason"], str)
    assert r["message"]


def test_blocked_with_invalid_action_falls_back_to_block():
    """self_check 의 reject 처럼 enum 밖 값이 blocked 로 흘러와도 계약을 지킨다(P-038)."""
    state = {
        "status": "blocked",
        "issues": [
            {"action": "reject", "reason": "regulation_risk", "message": "안내"}
        ],
    }
    assert assemble_response(state)["action"] == "block"


@pytest.mark.parametrize("action", ["block", "reask", "warn"])
def test_blocked_keeps_valid_actions(action):
    state = {
        "status": "blocked",
        "issues": [
            {"action": action, "reason": "need_clarification", "message": "안내"}
        ],
    }
    assert assemble_response(state)["action"] == action


# ── error ───────────────────────────────────────────────────────────────────
def test_copy_generation_failed_maps_per_d073():
    """④ D-073 확정 매핑: copy_generation_failed → provider_error.

    바꾸려면 코드가 아니라 decisions.md 에서 먼저 뒤집는다(D-046·D-286).
    """
    assert assemble_response(dict(STATE_ERROR))["reason"] == "provider_error"


def test_unmapped_internal_reason_falls_back_to_unknown():
    """계약 enum 밖의 내부 reason 은 unknown 으로 떨어진다(D-214)."""
    state = {
        "status": "error",
        "issues": [{"reason": "self_check_failed", "message": "근거 없음"}],
    }
    assert assemble_response(state)["reason"] == "unknown"


def test_unknown_status_becomes_error_not_blocked():
    """Model status 는 ok·blocked·error 뿐이다(§12.1).

    Generation status(generating 등)나 오타가 섞여도 조용히 blocked 로 떨어지면
    프론트엔드가 아무 안내 없이 차단 배너를 띄운다.
    """
    assert (
        assemble_response({"status": "generating", "result": {"x": 1}})["status"]
        == "error"
    )


@pytest.mark.parametrize(
    "state",
    [
        STATE_OK,
        STATE_BLOCKED,
        STATE_BLOCKED_NO_ISSUE,
        STATE_ERROR,
        {"status": "generating", "result": {"x": 1}},
        {},
    ],
)
def test_assemble_response_always_returns_contract_shape(state):
    r = assemble_response(dict(state))
    assert r["status"] in {"ok", "error", "blocked"}
    if r["status"] == "error":
        assert r["reason"] in ERROR_REASONS
        assert isinstance(r["message"], str) and r["message"]
    if r["status"] == "blocked":
        assert r["action"] in BLOCKED_ACTIONS and r["reason"] and r["message"]


# ═════════════════════════════════════════════════════════════════════════════
# B. run() 진입점 — 가짜 그래프 주입
#    ★ 프로덕션 build_basic.py 는 건드리지 않는다. main 이 import 한 이름만 바꾼다.
# ═════════════════════════════════════════════════════════════════════════════
class _FakeGraph:
    """LangGraph CompiledGraph 의 invoke() 만 흉내 낸다."""

    def __init__(self, box: dict):
        self._box = box

    def invoke(self, state: dict) -> dict:
        self._box["last_state"] = state
        scenario = self._box["scenario"]
        if scenario == "boom":
            raise RuntimeError("노드 내부 예외")
        return {**state, **_SCENARIOS[scenario]}


@pytest.fixture
def graph(monkeypatch):
    """가짜 그래프를 main 에 주입한다.

    monkeypatch 는 테스트 종료 시 자동 복원하므로 try/finally 가 필요 없다.
    reset_graph() 는 싱글턴이 테스트 간에 새어나가지 않게 한다(D-088 격리 원칙).
    """
    box = {"scenario": "ok", "builds": 0, "last_state": None}

    def factory():
        box["builds"] += 1
        return _FakeGraph(box)

    monkeypatch.setattr(main_mod, "build_basic_graph", factory)
    reset_graph()
    yield box
    reset_graph()


def _run(graph, scenario: str, **over) -> dict:
    graph["scenario"] = scenario
    return run({**REQUEST, **over})


@pytest.mark.parametrize(
    "scenario", ["ok", "blocked", "blocked_no_issue", "error", "boom"]
)
def test_run_never_raises_and_always_returns_contract_shape(graph, scenario):
    """⑤ run() 의 유일한 계약 — 어떤 경우에도 예외를 던지지 않는다."""
    r = _run(graph, scenario)
    assert r["status"] in {"ok", "error", "blocked"}
    if r["status"] == "error":
        assert r["reason"] in ERROR_REASONS
    if r["status"] == "blocked":
        assert r["action"] in BLOCKED_ACTIONS


def test_run_happy_path(graph):
    r = _run(graph, "ok")
    assert r["status"] == "ok" and len(r["proposals"]) == 3 and r["sources"] == []


@pytest.mark.parametrize(
    "drop", ["chatbot_type", "user_id", "question", "platform", "store"]
)
def test_missing_required_key_returns_error_without_touching_graph(graph, drop):
    """필수 키가 없으면 그래프를 부르지 않고 즉시 error — LLM 호출 0회·비용 0원."""
    r = run({k: v for k, v in REQUEST.items() if k != drop})
    assert r["status"] == "error" and r["reason"] in ERROR_REASONS
    assert graph["builds"] == 0, "요청 구성 실패인데 그래프를 컴파일했다"


def test_graph_is_compiled_once_across_requests(graph):
    """D-206 으로 서비스가 to_thread 를 쓰므로 동시 요청이 들어온다.

    요청마다 그래프를 다시 컴파일하면 p50 응답시간(§6 지표)이 그대로 늘어난다.
    llm.py 의 _get_client() 와 같은 원칙이다.
    """
    for _ in range(3):
        _run(graph, "ok")
    assert graph["builds"] == 1, f"그래프가 {graph['builds']}회 컴파일됐다"


def test_deadline_and_source_context_reach_the_graph(graph):
    """D-291 시간 예산과 컨설팅→광고 연계 Context 가 그래프까지 전달된다(D-306)."""
    _run(graph, "ok", source_context=SOURCE_CONTEXT)
    state = graph["last_state"]
    assert state["source_context"] == SOURCE_CONTEXT
    assert isinstance(state["deadline"], float) and state["deadline"] > 0
    assert state["extra"] == {}