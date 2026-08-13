# 질문 분석 노드 — 대명사 해소·재작성·정보충분성 판단
import json

from models.consult.graph.state import ConsultState
from models.consult.prompts.question_analysis import SYSTEM_PROMPT, build_user_prompt
from models.shared.llm import call_llm


def _fallback_analysis() -> dict:
    """폴백 시 매번 새 dict/list를 만든다 — 공유 객체를 반환하면 호출자가 리스트를
    수정했을 때 이후 요청의 폴백에도 그 값이 남는다."""
    return {"is_sufficient": True, "missing_info": []}


def question_analysis(state: ConsultState) -> dict:
    """질문을 가게 정보 기반으로 재작성하고 정보충분성을 판단한다.

    call_llm()이 재시도 끝에 실패하면(완전 실패) 예외를 그대로 전파한다.
    응답은 받았지만 JSON 파싱에 실패하거나 기대한 필드 타입이 아니면, 원본 질문을
    그대로 쓰고 정보 충분함으로 안전하게 폴백한다 — 질문 재작성 하나가 실패했다고
    전체 상담이 멈추면 안 되기 때문이다. json_mode=True로 호출해 파싱 실패 가능성을
    줄이지만, 필드 타입이 기대와 다를 가능성은 여전히 남아있어 폴백은 그대로 둔다.
    이번 호출의 토큰 사용량은 state["tokens_used"]에 누적한다.
    """
    question = state["question"]
    store = state["store"]

    raw, tokens = call_llm(SYSTEM_PROMPT, build_user_prompt(question, store), json_mode=True)
    rewritten_question, analysis = _parse_response(raw, question)

    return {
        "question": rewritten_question,
        "context": {"question_analysis": analysis},
        "tokens_used": state.get("tokens_used", 0) + tokens,
    }


def _parse_response(raw: str, original_question: str) -> tuple[str, dict]:
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return original_question, _fallback_analysis()

    if not isinstance(parsed, dict):
        return original_question, _fallback_analysis()

    rewritten = parsed.get("rewritten_question")
    is_sufficient = parsed.get("is_sufficient")
    missing_info = parsed.get("missing_info")

    valid = (
        isinstance(rewritten, str)
        and bool(rewritten.strip())
        and isinstance(is_sufficient, bool)
        and isinstance(missing_info, list)
        and all(isinstance(item, str) for item in missing_info)
        and is_sufficient == (len(missing_info) == 0)
    )
    if not valid:
        return original_question, _fallback_analysis()

    return rewritten, {"is_sufficient": is_sufficient, "missing_info": missing_info}
