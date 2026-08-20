"""
tests/integration/test_d7_model_boundary.py
— D7 서비스↔모델 경계 스모크 (소유: 서비스 개발 담당 · D-295)

★ 이 파일이 확인하는 것은 딱 하나다.
    "models/<chatbot>/main.py::run(request) 이 ModelResult 계약을 지키는 dict 를 돌려주는가"

★ 이 파일이 확인하지 않는 것
    · 카피 품질, 지표, 노드 동작 → 골든 데이터셋 평가 소관
    · assemble_response 의 분기 → models/basic/tests/test_main_contract.py 소관

★ 서비스 담당은 모델 측 단위·계약 테스트를 실행할 의무가 없다(D-295).
  모델 내부 구조(그래프·노드·state 키)를 전혀 몰라도 이 파일은 돌아야 한다.

실행:
    uv run --locked --all-groups pytest tests/integration/test_d7_model_boundary.py -q

    # 실제 LLM 을 태우는 스모크 1건까지 (OPENAI_API_KEY 필요, 비용 발생)
    RUN_LIVE_SMOKE=1 uv run --locked --all-groups pytest tests/integration -q
"""

import os

import pytest

ERROR_REASONS = {"timeout", "rate_limit", "provider_error", "unknown"}
BLOCKED_ACTIONS = {"block", "reask", "warn"}

BASIC_REQUEST = {
    "chatbot_type": "basic",
    "user_id": 1,
    "question": "여름 신메뉴 수박주스 홍보 문구 만들어줘",
    "platform": "instagram",
    "store": {"name": "카페 코드잇", "type": "카페",
              "address": "서울 강남구 역삼동", "lat": 37.5, "lng": 127.0},
}
CONSULT_REQUEST = {**BASIC_REQUEST, "chatbot_type": "consultant", "platform": None,
                   "question": "여름철 객단가를 올리려면 어떻게 해야 할까요?"}


def assert_model_result(payload) -> None:
    """ModelResult 계약(v0.3 §6.5·§6.6) 최소 형태를 확인한다.

    backend 스키마를 import 할 수 있으면 Pydantic 으로도 검증한다
    (테스트 파일에서의 backend import 는 D-210 이 허용한 예외다).
    """
    assert isinstance(payload, dict), f"dict 가 아니다: {type(payload)}"
    status = payload.get("status")
    assert status in {"ok", "blocked", "error"}, f"status={status!r}"

    if status == "ok":
        assert isinstance(payload.get("sources"), list), "sources 는 list 여야 한다"
        assert isinstance(payload.get("tokens_used"), int)
    elif status == "error":
        assert payload.get("reason") in ERROR_REASONS, f"reason={payload.get('reason')!r}"
        assert payload.get("message")
    else:
        assert payload.get("action") in BLOCKED_ACTIONS, f"action={payload.get('action')!r}"
        assert payload.get("reason") and isinstance(payload["reason"], str)
        assert payload.get("message")

    try:
        from backend.schemas.model import ModelResult  # noqa: PLC0415
    except ImportError:
        return
    ModelResult.model_validate(payload)


# ═════════════════════════════════════════════════════════════════════════════
# 1) 진입점이 계약대로 존재하는가 — LLM 호출 0회
# ═════════════════════════════════════════════════════════════════════════════
@pytest.mark.parametrize("module_path", ["models.basic.main", "models.consult.main"])
def test_entrypoint_exists_and_is_sync(module_path):
    """D-206: 모델은 동기 run() 을 제공하고 서비스가 asyncio.to_thread 로 감싼다."""
    import importlib
    import inspect

    module = importlib.import_module(module_path)
    run = getattr(module, "run", None)
    assert callable(run), f"{module_path}.run 이 없다"
    assert not inspect.iscoroutinefunction(run), (
        f"{module_path}.run 이 async 다 — 서비스는 to_thread 로 감싸므로 동기여야 한다(D-206)"
    )


@pytest.mark.parametrize("module_path,request_payload", [
    ("models.basic.main", BASIC_REQUEST),
    ("models.consult.main", CONSULT_REQUEST),
])
def test_run_never_raises_on_malformed_request(module_path, request_payload):
    """잘못된 요청에도 예외가 아니라 계약을 지키는 dict 가 나온다 — LLM 호출 0회."""
    import importlib

    run = importlib.import_module(module_path).run
    for broken in ({}, {"chatbot_type": "basic"}, {**request_payload, "store": None}):
        assert_model_result(run(broken))


# ═════════════════════════════════════════════════════════════════════════════
# 2) 실제 파이프라인 1회 — 비용이 발생하므로 명시적으로 켤 때만 돈다
# ═════════════════════════════════════════════════════════════════════════════
@pytest.mark.skipif(
    os.getenv("RUN_LIVE_SMOKE") != "1",
    reason="실제 LLM 호출 — RUN_LIVE_SMOKE=1 일 때만 실행 ($30 한도 보호)",
)
@pytest.mark.parametrize("module_path,request_payload", [
    ("models.basic.main", BASIC_REQUEST),
    ("models.consult.main", CONSULT_REQUEST),
])
def test_live_run_returns_model_result(module_path, request_payload):
    import importlib

    payload = importlib.import_module(module_path).run(request_payload)
    assert_model_result(payload)
    print(f"\n[{module_path}] status={payload['status']} "
          f"tokens={payload.get('tokens_used')}")
