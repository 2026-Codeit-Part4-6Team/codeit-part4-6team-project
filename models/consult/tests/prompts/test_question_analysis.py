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
    keyword로 뽑지 않는다는 조건→결론이 실제로 이어져 있어야 한다."""
    normalized = _normalized()
    assert '"이벤트 하나 해볼까요?" → keyword: null' in normalized
    for word in ("행사", "신메뉴"):
        assert word in normalized


def test_system_prompt_includes_positive_contrast_for_business_type_word() -> None:
    """업종명 반례가 너무 넓으면(예: "치킨"은 항상 업종명) 다른 업종 가게가 실제로
    "치킨"을 상품으로 언급하는 경우까지 억제할 수 있다(Codex 리뷰) — 실제 상품명은
    keyword로 뽑는다는 결론까지 이어져 있어야 한다."""
    normalized = _normalized()
    assert '"순살치킨"은 그 가게의 실제 상품명이므로 keyword로 뽑는다' in normalized
