"""기본 챗봇 조립 결과가 서비스 스키마를 실제로 통과하는지 확인한다(D-210).

노드 단위 테스트가 전부 초록불이어도 서비스에 붙이면 502가 나는 구조가
반복됐다(3안 개수·슬롯 불변조건·title 빈 문자열). 그 간극을 여기서 막는다.

⚠️ backend import 는 이 테스트 파일에서만 한다 — 프로덕션 코드가 backend 를
   import 하면 배포 단위 분리(D-031)가 깨진다.
"""

import pytest
from pydantic import ValidationError

from backend.schemas import (
    MODEL_RESULT_ADAPTER,
    BasicModelResult,
    BlockedResult,
    ErrorResult,
)
from models.basic.main import assemble_response
from models.basic.nodes.channel_format import channel_format_node

_STORE = {
    "name": "카페 코드잇",
    "type": "카페",
    "address": "서울 강남구 역삼동",
    "lat": 37.4979,
    "lng": 127.0276,
}

_COPY_FAILED_SLOT = {
    "copy": None,
    "image_b64": None,
    "error": {
        "field": "copy",
        "reason": "parse_failed",
        "message": "카피 생성에 실패했습니다.",
    },
}

_IMAGE_FAILED_SLOT = {
    "copy": "이미지만 실패한 카피",
    "image_b64": None,
    "error": {
        "field": "image",
        "reason": "content_policy",
        "message": "이미지 생성이 거부되었습니다.",
    },
}


def _ok_state(**overrides) -> dict:
    """channel_format_node 를 통과한 뒤의 정상 state 를 만든다."""
    base = {
        "status": "ok",
        "store": _STORE,
        "question": "강남역 카페인데 여름 신메뉴 홍보 문구 만들어줘",
        "result": {
            "title": "여름 신메뉴 홍보",
            "proposals": [
                {"copy": "시원한 여름 한 잔을 만나보세요.", "image_b64": None},
                {"copy": "오늘의 여름 메뉴를 소개합니다.", "image_b64": None},
                {"copy": "카페 코드잇에서 여름을 시작하세요.", "image_b64": None},
            ],
        },
        "sources": ["상권분석", "트렌드"],
        "tokens_used": 1520,
    }
    return {**base, **overrides}


# ── 1. 정상 경로 ────────────────────────────────────────────────


def test_ok_state_passes_service_contract():
    """정상 상태는 BasicModelResult 검증을 통과해야 한다."""
    result = MODEL_RESULT_ADAPTER.validate_python(
        assemble_response(_ok_state()), chatbot_type="basic"
    )

    assert isinstance(result, BasicModelResult)
    assert len(result.proposals) == 3
    assert result.suggested_chips == []  # Basic 은 반드시 빈 배열


def test_basic_result_must_not_carry_suggested_chips():
    """Basic 에 추천 칩이 섞이면 계약 위반(max_length=0)이다."""
    response = assemble_response(_ok_state())
    response["suggested_chips"] = ["칩1", "칩2", "칩3"]

    with pytest.raises(ValidationError):
        BasicModelResult.model_validate(response)


# ── 2. ★ proposals 3개 고정 (D-018·D-071) ──────────────────────


@pytest.mark.parametrize("count", [0, 1, 2, 4])
def test_proposal_count_other_than_three_is_rejected(count):
    """3안 고정 계약은 개수가 하나라도 어긋나면 502로 이어진다."""
    state = _ok_state()
    state["result"]["proposals"] = [
        {"copy": f"카피{i}", "image_b64": None} for i in range(count)
    ]

    with pytest.raises(ValidationError):
        BasicModelResult.model_validate(assemble_response(state))


def test_partial_failure_keeps_three_slots():
    """카피 1개·이미지 1개가 실패해도 슬롯 3개는 유지된다(D-018)."""
    state = _ok_state()
    state["result"]["proposals"] = [
        {"copy": "정상 카피", "image_b64": None},
        _IMAGE_FAILED_SLOT,
        _COPY_FAILED_SLOT,
    ]

    result = MODEL_RESULT_ADAPTER.validate_python(
        assemble_response(state), chatbot_type="basic"
    )

    assert len(result.proposals) == 3
    assert result.proposals[0].error is None
    assert result.proposals[1].error.field == "image"
    assert result.proposals[2].error.field == "copy"


# ── 3. ★ 슬롯 불변조건 (BasicProposal.validate_slot_state) ─────


def test_copy_failure_slot_must_null_both_copy_and_image():
    """error.field=copy 인데 copy 나 image_b64 가 남아 있으면 위반이다."""
    state = _ok_state()
    state["result"]["proposals"] = [
        {"copy": "정상1", "image_b64": None},
        {"copy": "정상2", "image_b64": None},
        {**_COPY_FAILED_SLOT, "image_b64": "남아있는-이미지"},  # ← 위반
    ]

    with pytest.raises(ValidationError):
        BasicModelResult.model_validate(assemble_response(state))


def test_image_failure_slot_must_keep_copy_and_clear_image():
    """error.field=image 인데 copy 가 비었으면 위반이다."""
    state = _ok_state()
    state["result"]["proposals"] = [
        {"copy": "정상1", "image_b64": None},
        {"copy": "정상2", "image_b64": None},
        {**_IMAGE_FAILED_SLOT, "copy": None},  # ← 위반
    ]

    with pytest.raises(ValidationError):
        BasicModelResult.model_validate(assemble_response(state))


def test_success_slot_must_have_nonblank_copy():
    """error 가 없는 슬롯에 빈 copy 가 오면 위반이다."""
    state = _ok_state()
    state["result"]["proposals"] = [
        {"copy": "정상1", "image_b64": None},
        {"copy": "정상2", "image_b64": None},
        {"copy": "   ", "image_b64": None},  # ← 위반
    ]

    with pytest.raises(ValidationError):
        BasicModelResult.model_validate(assemble_response(state))


def test_regulation_blocked_slot_satisfies_copy_failure_invariant():
    """법률 규제 차단 슬롯(D-196)이 copy 실패 불변조건을 지키는지 확인한다.

    image_b64 를 빠뜨리면 error.field=copy 인데 이미지가 남아 502가 난다.
    """
    blocked_slot = {
        "copy": None,
        "image_b64": None,
        "error": {
            "field": "copy",
            "reason": "content_policy",
            "message": "과장 광고 표현입니다.",
        },
    }
    state = _ok_state()
    state["result"]["proposals"] = [
        {"copy": "정상1", "image_b64": None},
        {"copy": "정상2", "image_b64": None},
        blocked_slot,
    ]

    result = MODEL_RESULT_ADAPTER.validate_python(
        assemble_response(state), chatbot_type="basic"
    )

    assert result.proposals[2].error.reason == "content_policy"


# ── 4. ★ 내부 키가 응답으로 새지 않는지 (D-196 회귀 방지) ──────


def test_internal_keys_do_not_leak_into_proposals():
    """score·clip_score·regulation 같은 내부 키는 응답에 없어야 한다.

    중첩 strict(P-018) 상태에서 이 키들이 새면 그대로 502다.
    """
    state = {
        "status": "ok",
        "question": "여름 신메뉴 홍보 문구 만들어줘",
        "ranked_copies": [
            {"copy": "카피1", "image_b64": None, "score": 4.8, "clip_score": 0.31},
            {
                "copy": "카피2",
                "image_b64": None,
                "score": 4.2,
                "regulation": {"action": "pass"},
            },
            {"copy": "카피3", "image_b64": None, "score": 3.9},
        ],
        "context": {"market": "상권 요약"},
        "tokens_used": 100,
    }

    formatted = channel_format_node(state)
    response = assemble_response({**state, **formatted})

    for proposal in response["proposals"]:
        assert set(proposal) <= {"copy", "image_b64", "error"}

    MODEL_RESULT_ADAPTER.validate_python(response, chatbot_type="basic")


# ── 5. title (D-209 폴백 원칙) ─────────────────────────────────


def test_title_must_not_be_blank():
    """title 은 min_length=1 이라 빈 문자열이면 계약 위반이다."""
    state = _ok_state()
    state["result"]["title"] = ""

    with pytest.raises(ValidationError):
        BasicModelResult.model_validate(assemble_response(state))


@pytest.mark.parametrize("rewritten", ["", "   "])
def test_blank_rewritten_question_still_yields_valid_title(rewritten):
    """question_analysis 가 빈 재작성 질문을 주더라도 title 이 비면 안 된다.

    question[:30] 을 그대로 쓰면 여기서 502가 난다 — 폴백이 필요하다.
    """
    state = {
        "status": "ok",
        "question": rewritten,
        "ranked_copies": [
            {"copy": "카피1", "image_b64": None},
            {"copy": "카피2", "image_b64": None},
            {"copy": "카피3", "image_b64": None},
        ],
        "context": {},
        "tokens_used": 10,
    }

    formatted = channel_format_node(state)
    response = assemble_response({**state, **formatted})

    assert response["title"].strip(), "title 이 비면 서비스에서 502가 난다"
    MODEL_RESULT_ADAPTER.validate_python(response, chatbot_type="basic")


# ── 6. blocked / error 경로 ───────────────────────────────────


@pytest.mark.parametrize(
    ("source", "action", "reason"),
    [
        ("input", "block", "input_blocked"),
        ("question_analysis", "reask", "insufficient_info"),
        ("regulation", "block", "exaggeration"),
        ("output", "block", "output_blocked"),
    ],
)
def test_blocked_state_becomes_blocked_result(source, action, reason):
    """차단 상태는 BlockedResult 형식으로 조립된다."""
    state = {
        "status": "blocked",
        "issues": [
            {
                "source": source,
                "action": action,
                "reason": reason,
                "message": "차단 사유 안내 문구",
            }
        ],
    }

    result = MODEL_RESULT_ADAPTER.validate_python(
        assemble_response(state), chatbot_type="basic"
    )

    assert isinstance(result, BlockedResult)
    assert result.action == action


def test_blocked_action_normalizes_to_block_when_outside_contract_enum():
    """action 이 block·reask·warn 밖이면(예: enum 밖 값) block으로 정규화되어
    계약 위반 자체가 발생하지 않는다."""
    state = {
        "status": "blocked",
        "issues": [
            {
                "source": "self_check",
                "action": "reject",  # ← enum 밖
                "reason": "self_check_failed",
                "message": "근거 부족",
            }
        ],
    }

    result = BlockedResult.model_validate(assemble_response(state))
    assert result.action == "block"


def test_blocked_message_must_not_be_blank():
    """message 는 min_length=1 이라 빈 문자열이면 위반이다."""
    state = {
        "status": "blocked",
        "issues": [
            {
                "source": "input",
                "action": "block",
                "reason": "input_blocked",
                "message": "",
            }
        ],
    }

    response = assemble_response(state)

    assert response["message"].strip(), "빈 message 는 서비스에서 502가 난다"
    MODEL_RESULT_ADAPTER.validate_python(response, chatbot_type="basic")


@pytest.mark.parametrize(
    "reason", ["timeout", "rate_limit", "provider_error", "unknown"]
)
def test_error_reason_inside_contract_enum_passes(reason):
    """ErrorResult.reason 은 계약 enum 4종만 허용된다."""
    state = {
        "status": "error",
        "issues": [
            {
                "source": "copy_gen",
                "reason": reason,
                "message": "카피 생성 중 오류가 발생했습니다.",
            }
        ],
    }

    result = MODEL_RESULT_ADAPTER.validate_python(
        assemble_response(state), chatbot_type="basic"
    )

    assert isinstance(result, ErrorResult)
    assert result.reason == reason


def test_copy_generation_failed_is_mapped_to_contract_reason():
    """내부 reason(copy_generation_failed)은 enum 밖이라 매핑돼야 한다(D-073)."""
    state = {
        "status": "error",
        "issues": [
            {
                "source": "copy_gen",
                "reason": "copy_generation_failed",
                "message": "카피 생성에 반복적으로 실패했습니다.",
            }
        ],
    }

    response = assemble_response(state)

    assert response["reason"] in {
        "timeout",
        "rate_limit",
        "provider_error",
        "unknown",
    }, "내부 reason 을 그대로 내보내면 502가 난다"
    MODEL_RESULT_ADAPTER.validate_python(response, chatbot_type="basic")


# ── 7. 방어 ───────────────────────────────────────────────────


def test_empty_result_is_converted_to_error_not_ok():
    """카피가 하나도 없는데 ok 로 내보내면 계약이 깨진다."""
    response = assemble_response({"status": "ok", "question": "질문", "result": {}})

    assert response["status"] == "error"
    with pytest.raises(ValidationError):
        BasicModelResult.model_validate(response)
