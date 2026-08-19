# models/consult/tests/test_main.py
"""run()이 어떤 실패든 예외를 밖으로 새어나가게 하지 않고 계약을 지키는 dict를
돌려주는지 확인한다 — assemble_response 자체의 조립 로직은 test_assemble_response.py가
따로 검증하므로 여기서는 run()의 안전망 범위만 다룬다."""
from unittest.mock import MagicMock, patch

from models.consult.main import build_initial_state, run

_STORE = {"name": "카페 코드잇", "type": "카페", "address": "서울 강남구 역삼동",
          "lat": 37.4979, "lng": 127.0276}


def _request(**overrides) -> dict:
    base = {
        "chatbot_type": "consultant",
        "user_id": 1,
        "question": "주변 경쟁사는 얼마나 되나요?",
        "store": _STORE,
    }
    return {**base, **overrides}


def test_build_initial_state_normalizes_optional_extra() -> None:
    request = _request(extra=None)

    assert build_initial_state(request) == {
        "chatbot_type": "consultant",
        "user_id": 1,
        "question": "주변 경쟁사는 얼마나 되나요?",
        "store": _STORE,
        "extra": {},
        "tokens_used": 0,
    }


@patch("models.consult.main.build_initial_state")
@patch("models.consult.main.build_consultant")
def test_run_invokes_graph_with_shared_initial_state(
    mock_build_consultant,
    mock_build_initial_state,
) -> None:
    initial_state = {"shared": "state"}
    mock_build_initial_state.return_value = initial_state
    mock_graph = MagicMock()
    mock_graph.invoke.return_value = {
        "status": "error",
        "issues": [{"reason": "unknown", "message": "실패"}],
    }
    mock_build_consultant.return_value = mock_graph

    run(_request())

    mock_build_initial_state.assert_called_once_with(_request())
    mock_graph.invoke.assert_called_once_with(initial_state)


@patch("models.consult.main.build_consultant")
def test_ok_state_is_assembled_into_ok_response(mock_build_consultant) -> None:
    """그래프가 정상 완료되면 assemble_response를 거친 ok 응답을 돌려준다."""
    mock_graph = MagicMock()
    mock_graph.invoke.return_value = {
        "store": _STORE,
        "result": {
            "title": "역삼동 카페 전략",
            "summary": "반경 500m 동일 업종 177곳입니다.",
            "actions": [{"type": "menu", "content": "신메뉴를 출시하세요."}],
            "reasons": ["반경 500m 내 동일 업종 177곳"],
        },
        "sources": ["상권분석"],
        "tokens_used": 500,
        "suggested_chips": ["a?", "b?", "c?"],
    }
    mock_build_consultant.return_value = mock_graph

    response = run(_request())

    assert response["status"] == "ok"
    assert response["strategy"]["summary"].startswith("반경")


@patch("models.consult.main.build_consultant")
def test_graph_invoke_exception_becomes_error_response(mock_build_consultant) -> None:
    """그래프 실행 자체가 예외를 던지면 ErrorResult 형태로 감싼다."""
    mock_graph = MagicMock()
    mock_graph.invoke.side_effect = RuntimeError("그래프 내부 오류")
    mock_build_consultant.return_value = mock_graph

    response = run(_request())

    assert response["status"] == "error"
    assert response["reason"] == "unknown"


def test_malformed_request_becomes_error_response_not_raw_exception() -> None:
    """request에 필수 키(store)가 빠져도 KeyError가 그대로 새어나가면 안 된다 —
    run()은 "어떤 실패든 계약을 지키는 dict를 돌려준다"고 약속했다."""
    malformed_request = _request()
    del malformed_request["store"]

    response = run(malformed_request)

    assert response["status"] == "error"


@patch("models.consult.main.build_consultant")
def test_malformed_final_state_becomes_error_response_not_raw_exception(
    mock_build_consultant,
) -> None:
    """assemble_response 내부에서 조립이 실패해도(예: summary는 있는데 actions가
    없는 예상 밖 state) 예외가 그대로 새어나가면 안 된다."""
    mock_graph = MagicMock()
    mock_graph.invoke.return_value = {
        "store": _STORE,
        "result": {"title": "제목", "summary": "요약만 있고 actions가 없음"},
    }
    mock_build_consultant.return_value = mock_graph

    response = run(_request())

    assert response["status"] == "error"
