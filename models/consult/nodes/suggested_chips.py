# 추천 질문 칩 3종 처리 노드
import json

from models.consult.graph.state import ConsultState
from models.consult.prompts.suggested_chips import SYSTEM_PROMPT, build_user_prompt
from models.shared.llm import call_llm

_NUM_CHIPS = 3
_FALLBACK_CHIPS = [
    "어떤 이벤트가 효과적일까요?",
    "가격을 어떻게 책정하면 좋을까요?",
    "주요 타겟 고객층은 어떻게 설정해야 할까요?",
]


def suggested_chips(state: ConsultState) -> dict:
    """질문 맥락에 맞는 후속 질문 3개를 생성해 추천 칩으로 반환한다.

    서비스 계약(backend/schemas.py의 ConsultantModelResult.suggested_chips)이
    정확히 3개·각각 비어있지 않은 문자열을 요구한다. 응답이 그 형식을 지키지
    않으면(개수 오류·빈 문자열 등) 업종 범용 고정 질문 3개로 폴백한다 —
    question_analysis와 동일한 원칙으로, 칩 생성 하나가 형식을 어겼다고
    전체 상담이 멈추면 안 되기 때문이다.

    이 노드는 question_analysis 직후(상권·트렌드 조회 이전)에 실행되므로
    context["market"]/context["trend"]는 아직 없다 — question_analysis가 남긴
    missing_info만 참고해, 부족한 정보를 채우는 칩을 하나 포함하도록 유도한다.

    call_llm()이 재시도 끝에 실패하면(완전 실패) 예외를 그대로 전파한다
    (question_analysis/strategy와 동일 원칙 — 인프라 장애는 숨기지 않는다).
    """
    question = state["question"]
    store = state["store"]
    missing_info = state.get("context", {}).get("question_analysis", {}).get("missing_info", [])

    raw, tokens = call_llm(
        SYSTEM_PROMPT,
        build_user_prompt(question, store, missing_info),
        json_mode=True,
        deadline=state.get("deadline"),
    )
    chips = _parse_chips(raw)

    return {
        "suggested_chips": chips,
        "tokens_used": state.get("tokens_used", 0) + tokens,
    }


def _parse_chips(raw: str) -> list[str]:
    """정확히 3개의 비어있지 않은 문자열인지 검증하고 공백을 정리한 새 리스트를
    반환한다. 형식이 안 맞으면 고정 폴백 질문 3개를 반환한다(매번 새 리스트를
    만들어 호출자가 수정해도 다음 호출에 영향 없게 한다)."""
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return list(_FALLBACK_CHIPS)

    if not isinstance(parsed, dict):
        return list(_FALLBACK_CHIPS)

    chips = parsed.get("chips")
    if not isinstance(chips, list) or len(chips) != _NUM_CHIPS:
        return list(_FALLBACK_CHIPS)

    normalized = []
    for chip in chips:
        if not isinstance(chip, str) or not chip.strip():
            return list(_FALLBACK_CHIPS)
        normalized.append(chip.strip())

    return normalized
