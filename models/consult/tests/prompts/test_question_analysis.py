# models/consult/prompts/question_analysis.py 테스트 — trend keyword 과대추출 반례가
# 프롬프트에서 삭제되거나 의미가 반대로 바뀌는 회귀를 잡는다(D8 60문항 실측 불일치
# 9건의 원인, Codex 리뷰).
from models.consult.prompts.question_analysis import SYSTEM_PROMPT


def _normalized() -> str:
    """줄바꿈으로 인한 우연한 불일치를 피하려고 공백을 하나로 뭉친다 —
    조건과 결론이 실제로 이어져 있는지(단어 존재만이 아니라) 확인하는 데 쓴다."""
    return " ".join(SYSTEM_PROMPT.split())


def test_system_prompt_excludes_business_type_words_as_keyword() -> None:
    """가게 업종명 자체는 특정 상품이 아니므로 keyword로 뽑지 않는다는 조건과
    결론(keyword: null)이 실제로 이어져 있어야 한다 — 단어만 확인하면 결론이
    반대로("치킨"도 keyword로 뽑아라) 바뀌는 회귀를 못 잡는다(Codex 리뷰)."""
    normalized = _normalized()
    assert '"치킨집 홍보 어떻게 하죠?"라고 물으면 keyword: null' in normalized
    assert "업종명일 뿐 특정 메뉴가 아니다" in normalized


def test_system_prompt_excludes_generic_concept_words_as_keyword() -> None:
    """ "이벤트"·"행사"·"신메뉴"처럼 무엇을 가리키는지 특정하지 않는 범용 개념어도
    keyword로 뽑지 않는다는 조건→결론이 실제로 이어져 있어야 한다. 단, 이 규칙은
    구체 메뉴·상품·이슈가 함께 없을 때만 적용된다는 범위 제한이 살아있어야 한다
    (v2 섹션A — 혼합 질문에서 범위가 조용히 넓어지는 회귀 방지)."""
    normalized = _normalized()
    assert '"이벤트 하나 해볼까요?" → keyword: null' in normalized
    assert '구체 메뉴·상품·이슈는 없고' in normalized
    assert '범용 개념어만 대상으로 제시된 경우(예: "이벤트", "행사", "신메뉴"' in normalized


def test_system_prompt_declares_specific_target_priority_over_generic_word() -> None:
    """keyword 후보 중 구체 메뉴·상품·이슈가 범용 개념어보다 우선한다는 선언 자체가
    프롬프트에 있어야 한다 — "단독으로 등장했을 때"처럼 애매한 표현 대신 명시적
    우선순위 문장으로 규칙을 표현한다(v2 섹션A, 리뷰 반영: "단독"은 문장에 다른
    단어가 있으면 LLM이 다르게 해석할 수 있어 모호함)."""
    normalized = _normalized()
    assert "keyword 후보의 우선순위는 구체 메뉴·상품·이슈가 범용 개념어보다 높다" in normalized


def test_system_prompt_extracts_specific_product_when_mixed_with_generic_word() -> None:
    """범용 개념어와 구체 상품명이 한 문장에 함께 나오면 범용어를 무시하고 구체
    상품명을 keyword로 뽑는다는 조건→결론이 실제로 이어져 있어야 한다(C-047 —
    "디지털펌"+"이벤트" 혼합 질문에서 keyword가 null로 과소추출되던 회귀의 재발
    방지, v2 섹션A)."""
    normalized = _normalized()
    assert '"디지털펌 손님을 늘리려면 어떤 이벤트가 좋을까요?" → keyword: "디지털펌"' in normalized
    assert '"아이스라테 신메뉴 행사를 해볼까요?" → keyword: "아이스라테"' in normalized


def test_system_prompt_includes_positive_contrast_for_business_type_word() -> None:
    """업종명 반례가 너무 넓으면(예: "치킨"은 항상 업종명) 다른 업종 가게가 실제로
    "치킨"을 상품으로 언급하는 경우까지 억제할 수 있다(Codex 리뷰) — 실제 상품명은
    keyword로 뽑는다는 결론까지 이어져 있어야 한다."""
    normalized = _normalized()
    assert '"순살치킨"은 그 가게의 실제 상품명이므로 keyword로 뽑는다' in normalized
