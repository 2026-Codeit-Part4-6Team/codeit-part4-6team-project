# CommonState/StoreInfo 필드 구성 테스트
import operator
from typing import get_args, get_type_hints

from models.shared.state_common import CommonState, StoreInfo, merge_dicts


def test_store_info_has_expected_fields() -> None:
    """서비스 담당이 요청 JSON으로 실어 보내는 가게 정보 필드가 갖춰져 있다."""
    assert set(StoreInfo.__annotations__.keys()) == {
        "name",
        "type",
        "address",
        "lat",
        "lng",
    }


def test_common_state_has_expected_fields() -> None:
    """두 챗봇이 공유하는 공통 필드가 PM 제시안대로 갖춰져 있다."""
    assert set(CommonState.__annotations__.keys()) == {
        "chatbot_type",
        "user_id",
        "question",
        "store",
        "platform",
        "extra",
        "context",
        "result",
        "sources",
        "tokens_used",
        "validation",
        "source_gen_id",
    }


def test_only_input_fields_are_required() -> None:
    """서비스 최초 요청에 항상 있는 입력 필드만 필수여야 파이프라인 중간 상태도 유효하다.

    platform은 Basic만 필수(Consultant는 생략 가능), extra는 둘 다 선택이라
    CommonState 레벨에서는 둘 다 NotRequired로 둔다(D1 회의 확정 사항).
    """
    assert CommonState.__required_keys__ == frozenset(
        {"chatbot_type", "user_id", "question", "store"}
    )
    assert CommonState.__optional_keys__ == frozenset(
        {
            "platform",
            "extra",
            "context",
            "result",
            "sources",
            "tokens_used",
            "validation",
            "source_gen_id",
        }
    )


def _reducer_of(field: str):
    hints = get_type_hints(CommonState, include_extras=True)
    annotated = get_args(hints[field])[0]
    return annotated.__metadata__[0]


def test_context_and_validation_use_merge_dict_reducer() -> None:
    """병렬 조회·검증 노드가 각자 다른 키를 채워도 LangGraph가 병합할 수 있어야 한다.

    TODO(섹션 2, LangGraph 의존성 추가 시): 여기서는 Annotated 메타데이터만 확인한다.
    실제 StateGraph를 컴파일해 병렬 노드 병합 결과까지 검증하는 통합 테스트를 추가한다.
    """
    assert _reducer_of("context") is merge_dicts
    assert _reducer_of("validation") is merge_dicts


def test_sources_uses_list_concat_reducer() -> None:
    """병렬 노드가 각자 근거 출처를 추가해도 누락 없이 이어붙여야 한다."""
    assert _reducer_of("sources") is operator.add


def test_merge_dicts_combines_without_dropping_keys() -> None:
    assert merge_dicts({"market": 1}, {"trend": 2}) == {"market": 1, "trend": 2}
