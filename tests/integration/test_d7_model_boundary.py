"""D7 Service↔Model 공개 경계 smoke.

모델 내부 Graph/Node/State가 아니라 models.<chatbot>.main.run(request)의
sync entrypoint 및 Service ModelResult 계약만 검증한다.
"""

import importlib
import inspect
import os

import pytest

from backend.schemas import MODEL_RESULT_ADAPTER


pytestmark = pytest.mark.skipif(
    os.getenv("RUN_MODEL_BOUNDARY_SMOKE") != "1",
    reason=(
        "D7 단독 브랜치는 모델 PR과 독립 merge 가능해야 함 — "
        "RUN_MODEL_BOUNDARY_SMOKE=1 인 통합 workspace에서 실행"
    ),
)


BASIC_REQUEST = {
    "chatbot_type": "basic",
    "user_id": 1,
    "question": "여름 신메뉴 수박주스 홍보 문구 만들어줘",
    "platform": "instagram",
    "store": {
        "name": "카페 코드잇",
        "type": "카페",
        "address": "서울 강남구 역삼동",
        "lat": 37.5,
        "lng": 127.0,
    },
}
CONSULT_REQUEST = {
    **BASIC_REQUEST,
    "chatbot_type": "consultant",
    "platform": None,
    "question": "여름철 객단가를 올리려면 어떻게 해야 할까요?",
}


def assert_model_result(payload: object, chatbot_type: str) -> None:
    """실제 Service adapter까지 통과하는 ModelResult인지 검증한다."""
    assert isinstance(payload, dict), f"dict 가 아니다: {type(payload)}"
    MODEL_RESULT_ADAPTER.validate_python(payload, chatbot_type=chatbot_type)


@pytest.mark.parametrize("module_path", ["models.basic.main", "models.consult.main"])
def test_entrypoint_exists_and_is_sync(module_path):
    module = importlib.import_module(module_path)
    run = getattr(module, "run", None)

    assert callable(run), f"{module_path}.run 이 없다"
    assert not inspect.iscoroutinefunction(run), (
        f"{module_path}.run 이 async 다 — Service가 asyncio.to_thread로 감싼다"
    )


@pytest.mark.parametrize(
    "module_path,request_payload",
    [
        ("models.basic.main", BASIC_REQUEST),
        ("models.consult.main", CONSULT_REQUEST),
    ],
)
def test_run_never_raises_on_malformed_request(module_path, request_payload):
    run = importlib.import_module(module_path).run
    chatbot_type = request_payload["chatbot_type"]

    for broken in ({}, {"chatbot_type": chatbot_type}, {**request_payload, "store": None}):
        assert_model_result(run(broken), chatbot_type)


@pytest.mark.skipif(
    os.getenv("RUN_LIVE_SMOKE") != "1",
    reason="실제 LLM 호출 — RUN_LIVE_SMOKE=1 일 때만 실행",
)
@pytest.mark.parametrize(
    "module_path,request_payload",
    [
        ("models.basic.main", BASIC_REQUEST),
        ("models.consult.main", CONSULT_REQUEST),
    ],
)
def test_live_run_returns_model_result(module_path, request_payload):
    payload = importlib.import_module(module_path).run(request_payload)
    assert_model_result(payload, request_payload["chatbot_type"])
