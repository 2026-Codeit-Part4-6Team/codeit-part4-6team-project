# 마케팅 전략 제안 노드 (가장 중요) — D4 섹션 1~4
import json

from models.consult.graph.state import ConsultState
from models.consult.prompts.strategy import SYSTEM_PROMPT, build_user_prompt
from models.shared.llm import call_llm

_VALID_ACTION_TYPES = {"menu", "promotion", "target", "other"}


def strategy(state: ConsultState) -> dict:
    """질문·가게 정보·(있으면) 상권 데이터로 전략(summary+actions)을 생성한다.

    상권 데이터(context["market"])가 없으면(조회 실패, 노드 조기 실행 등) 프롬프트에서
    해당 섹션이 통째로 빠지고 질문·가게 정보만으로 생성한다 — 부분 성공 허용 원칙.
    트렌드 데이터 연동(D5/D6)은 아직 하지 않는다. 근거(reasons) 필수화(섹션 5)도 다음 단계다.

    call_llm()이 재시도 끝에 실패하면(완전 실패) 예외를 그대로 전파한다
    (질문 분석 노드와 동일 원칙 — 인프라 장애는 숨기지 않는다).
    응답이 JSON이 아니거나 summary/actions가 API 계약(v0.3) 형식을 어기면 예외를 던져
    즉시 실패시킨다 — 가장 중요한 노드라 폴백 대신 엄격하게 방어한다. 자동 재시도는
    근거(reasons) 검증과 함께 섹션 5에서 붙인다.
    이번 호출의 토큰 사용량은 state["tokens_used"]에 누적한다.
    """
    question = state["question"]
    store = state["store"]
    market = state.get("context", {}).get("market")

    raw, tokens = call_llm(
        SYSTEM_PROMPT, build_user_prompt(question, store, market), json_mode=True
    )

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError("LLM이 유효한 JSON을 반환하지 않았습니다.") from exc

    summary = parsed.get("summary") if isinstance(parsed, dict) else None
    if not isinstance(summary, str) or not summary.strip():
        raise ValueError("LLM이 빈 전략 요약을 반환했습니다.")

    actions = _parse_actions(parsed.get("actions"))
    if actions is None:
        raise ValueError("LLM이 유효한 actions 배열을 반환하지 않았습니다.")

    return {
        "result": {"summary": summary.strip(), "actions": actions},
        "tokens_used": state.get("tokens_used", 0) + tokens,
    }


def _parse_actions(actions: object) -> list[dict] | None:
    """actions가 API 계약(type 4종 enum, content 1개 이상, 1~3개)을 지키는지 검증하고
    공백을 정리한 새 리스트를 반환한다. 형식이 안 맞으면 None을 반환한다."""
    if not isinstance(actions, list) or not (1 <= len(actions) <= 3):
        return None

    normalized = []
    for action in actions:
        if not isinstance(action, dict):
            return None
        action_type = action.get("type")
        content = action.get("content")
        if not isinstance(action_type, str) or action_type not in _VALID_ACTION_TYPES:
            return None
        if not isinstance(content, str) or not content.strip():
            return None
        normalized.append({"type": action_type, "content": content.strip()})

    return normalized
