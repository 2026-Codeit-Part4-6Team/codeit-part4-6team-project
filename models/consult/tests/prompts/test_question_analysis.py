# models/consult/prompts/question_analysis.py 테스트 — trend keyword 과대추출 반례가
# 프롬프트에서 삭제되는 회귀를 잡는다(D8 60문항 실측 불일치 9건의 원인, Codex 리뷰).
from models.consult.prompts.question_analysis import SYSTEM_PROMPT


def test_system_prompt_excludes_business_type_words_as_keyword() -> None:
    """가게 업종명 자체는 특정 상품이 아니므로 keyword로 뽑지 않는다는 반례가 있어야
    한다 — 없으면 C-004·C-007·C-012·C-034 패턴이 재발한다."""
    assert "치킨" in SYSTEM_PROMPT
    assert "업종" in SYSTEM_PROMPT


def test_system_prompt_excludes_generic_concept_words_as_keyword() -> None:
    """ "이벤트"·"행사"·"신메뉴"처럼 무엇을 가리키는지 특정하지 않는 범용 개념어도
    keyword로 뽑지 않는다는 반례가 있어야 한다 — 없으면 C-023·C-041·C-042·C-044·
    C-045 패턴이 재발한다."""
    for word in ("이벤트", "행사", "신메뉴"):
        assert word in SYSTEM_PROMPT


def test_system_prompt_includes_positive_contrast_for_business_type_word() -> None:
    """업종명 반례가 너무 넓으면(예: "치킨"은 항상 업종명) 다른 업종 가게가 실제로
    "치킨"을 상품으로 언급하는 경우까지 억제할 수 있다(Codex 리뷰) — 반례가 가게
    자신의 업종을 가리킬 때로 조건이 좁혀져 있고, 실제 상품명은 그대로 뽑는다는
    대조 예시가 있어야 한다."""
    assert "순살치킨" in SYSTEM_PROMPT
    assert "가게 정보" in SYSTEM_PROMPT
