# ConsultState 필드 구성 테스트
from graph.state_common import CommonState
from model_consult.graph.state import ConsultState


def test_consult_state_extends_common_state() -> None:
    """ConsultState는 CommonState 필드를 전부 포함한다."""
    assert set(CommonState.__annotations__.keys()) <= set(
        ConsultState.__annotations__.keys()
    )


def test_consult_state_has_consult_specific_fields() -> None:
    """컨설턴트 전용 필드(재생성 루프·추천 질문 칩)가 갖춰져 있다.

    전략 결과는 별도 필드 없이 상속받은 result에 담으므로 여기 포함되지 않는다.
    """
    consult_only = set(ConsultState.__annotations__.keys()) - set(
        CommonState.__annotations__.keys()
    )
    assert consult_only == {"retry_count", "suggested_chips"}


def test_consult_specific_fields_are_not_required() -> None:
    """재생성 루프 카운터 등은 파이프라인이 나중에 채우므로 최초 상태 생성 시 필수가 아니어야 한다."""
    consult_only = {"retry_count", "suggested_chips"}
    assert consult_only <= ConsultState.__optional_keys__
    assert ConsultState.__required_keys__ == CommonState.__required_keys__
