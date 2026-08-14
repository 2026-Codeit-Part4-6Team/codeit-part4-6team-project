# 마케팅 전략 제안 노드 (가장 중요) — D4 섹션 1~5
import json

from models.consult.graph.state import ConsultState
from models.consult.prompts.strategy import RETRY_REASONS_HINT, SYSTEM_PROMPT, build_user_prompt
from models.shared.llm import call_llm

_VALID_ACTION_TYPES = {"menu", "promotion", "target", "other"}
_MAX_REASONS_RETRIES = 2  # 근거 부족 재생성 상한(SDP §6.5)


def strategy(state: ConsultState) -> dict:
    """질문·가게 정보·(있으면) 상권 데이터로 전략(summary+actions+reasons)을 생성한다.

    상권 데이터(context["market"])·트렌드 데이터(context["trend"])가 없으면(조회 실패,
    keyword 없음, 노드 조기 실행 등) 프롬프트에서 해당 섹션이 통째로 빠지고 나머지
    데이터만으로 생성한다 — 부분 성공 허용 원칙.

    call_llm()이 재시도 끝에 실패하면(완전 실패) 예외를 그대로 전파한다
    (질문 분석 노드와 동일 원칙 — 인프라 장애는 숨기지 않는다).
    응답이 JSON이 아니거나 summary/actions가 API 계약(v0.3) 형식을 어기면 그 즉시
    예외를 던진다 — 가장 중요한 노드라 폴백 대신 엄격하게 방어한다.

    reasons만은 다르게 취급한다 — JSON 구조 자체는 유효한데 근거가 비어 있으면
    "형식 오류"가 아니라 "품질 부족"으로 보고, call_llm()을 다시 호출해 재생성한다
    (SDP §6.5, 최대 2회). 재시도 시에는 RETRY_REASONS_HINT를 프롬프트에 덧붙여 근거를
    포함하라고 명시적으로 요구한다. 2회 재생성 후에도 근거가 없으면 그때는 예외를 던진다
    (DoD상 reasons는 반드시 포함돼야 하므로). 이 재시도는 strategy 노드 내부에서만
    반복되며, 그래프 조건부 엣지는 쓰지 않는다 — strategy_check 노드는 D9에 별도로
    구현될 "근거 유무·실행 가능성·LLM Judge" 검증이라 이번 범위와 다르다.
    여러 번 호출한 토큰 사용량은 모두 합산해 state["tokens_used"]에 누적하고,
    실제 재생성 횟수는 state["retry_count"]에 기록한다.
    """
    question = state["question"]
    store = state["store"]
    context = state.get("context", {})
    market = context.get("market")
    trend = context.get("trend")
    base_user_prompt = build_user_prompt(question, store, market, trend)
    deadline = state.get("deadline")

    total_tokens = 0
    retry_count = 0

    while True:
        user_prompt = (
            base_user_prompt if retry_count == 0 else f"{base_user_prompt}\n\n{RETRY_REASONS_HINT}"
        )
        raw, tokens = call_llm(SYSTEM_PROMPT, user_prompt, json_mode=True, deadline=deadline)
        total_tokens += tokens

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

        reasons = _parse_reasons(parsed.get("reasons"))
        if reasons is not None:
            break
        if retry_count >= _MAX_REASONS_RETRIES:
            raise ValueError("LLM이 재생성 후에도 근거(reasons)를 반환하지 않았습니다.")
        retry_count += 1

    return {
        "result": {"summary": summary.strip(), "actions": actions, "reasons": reasons},
        "tokens_used": state.get("tokens_used", 0) + total_tokens,
        # 다른 노드(D9 strategy_check)도 같은 키에 쓸 예정이라 덮어쓰지 않고 누적한다
        # (PM 리뷰, PR #93).
        "retry_count": state.get("retry_count", 0) + retry_count,
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


def _parse_reasons(reasons: object) -> list[str] | None:
    """reasons가 1개 이상의 비어있지 않은 문자열 리스트인지 검증하고 공백을 정리한
    새 리스트를 반환한다. 형식이 안 맞거나 비어 있으면 None을 반환한다(재생성 신호)."""
    if not isinstance(reasons, list) or len(reasons) == 0:
        return None

    normalized = []
    for reason in reasons:
        if not isinstance(reason, str) or not reason.strip():
            return None
        normalized.append(reason.strip())

    return normalized
