# 마케팅 전략 제안 노드 (가장 중요) — D4 섹션 1~5
import json

from models.consult.config import MAX_ACTIONS, MIN_ACTIONS
from models.consult.graph.state import ConsultState
from models.consult.prompts.strategy import (
    RETRY_ACTIONS_HINT,
    RETRY_REASONS_HINT,
    SYSTEM_PROMPT,
    build_user_prompt,
)
from models.shared.llm import call_llm

_VALID_ACTION_TYPES = {"menu", "promotion", "target", "other"}
# reasons(SDP §6.5)와 actions 0개 재생성(D-139 후속, PM 승인)이 합산해서 쓰는 상한.
# 개별 예산을 따로 두면 최초 호출 포함 최대 4회까지 늘어나 D-144가 전제한
# "strategy 최대 3회 + 429 백오프"의 60초 예산을 넘길 수 있다(Codex 리뷰).
_MAX_RETRIES = 2


def normalize_title(title: object, store_name: str) -> str:
    """title이 없거나 공백뿐이면 가게 이름 기반 기본 제목으로 폴백한다.

    summary/actions/reasons와 달리 title은 형식 오류로 전체 응답을 실패시키지
    않는다 — 제목 하나 때문에 좋은 전략을 버리면 안 된다(PM 리뷰, D7 계약
    정합성). main.py의 assemble_response()도 이 함수를 그대로 써서, 파싱 직후와
    최종 조립 시점의 검증 수준이 서로 달라지지 않게 한다(Codex 리뷰로 발견 —
    조립 단계는 원래 truthy 여부만 봐서 공백 문자열("   ")도 통과시켰었다).
    """
    if not isinstance(title, str) or not title.strip():
        return f"{store_name} 마케팅 전략"
    return title.strip()


def strategy(state: ConsultState) -> dict:
    """질문·가게 정보·(있으면) 상권 데이터로 전략(title+summary+actions+reasons)을 생성한다.

    title은 backend/schemas.py의 ConsultantModelResult.title(min_length=1 필수)에
    대응한다 — 지금까지는 mock_chatbot.py가 대신 채워줘서 통과했지만, 계약상 모델이
    반환해야 하는 필드다(D7 계약 정합성 점검, PM 리뷰). 다만 summary/actions/reasons와
    달리 형식 오류로 전체 응답을 실패시키지 않고 가게 이름 기반 기본 제목으로 폴백한다
    — 제목 하나 때문에 좋은 전략을 버리면 안 되기 때문이다.

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

    actions 개수(MIN_ACTIONS~MAX_ACTIONS=1~3)가 계약을 벗어나면 PM 승인(D-139 후속,
    decisions.md 기록 대기 중)에 따라 두 가지로 나눠 처리한다 — 이 처리는 "형식
    오류"가 아니라 "확률적 변동"으로 재분류됐다: D8 60문항 실측에서 status=error
    5건이 전부 이 원인이었는데(프롬프트의 "1~3개만" 지시를 LLM이 가끔 무시함),
    재시도하면 통과한다는 것 자체가 "재시도해도 똑같이 깨진다"는 D-139의 형식
    오류 전제와 다르다는 근거였다.
      - 4개 이상(초과): LLM 재호출 없이 앞 MAX_ACTIONS개만 잘라 그대로 쓴다
        ("truncated") — 많이 낸 것이지 답을 못 낸 게 아니므로 재생성이 불필요하다.
      - 0개(미달): 잘라낼 게 없으므로 재생성한다("retry", RETRY_ACTIONS_HINT 부가).
    실측 확인 결과 5건 전부 0개 케이스였고 초과 케이스는 관찰되지 않았다(2026-08-21
    재확인, 15회 샘플링 중 초과 0건). 다른 actions 오류(enum 밖 type, content 누락
    등)는 형식 자체가 신뢰할 수 없다고 보고 재생성 없이 즉시 예외를 던진다.

    actions 0개 재생성과 reasons 부족 재생성은 재생성 예산(_MAX_RETRIES=2)을
    함께 쓴다 — 따로 두면 최초 호출 포함 최대 4회까지 늘어나 D-144가 전제한 60초
    예산을 넘길 위험이 있다(Codex 리뷰). 합산 상한을 넘기면 그 시점의 오류
    종류에 맞는 예외를 던진다.

    여러 번 호출한 토큰 사용량은 모두 합산해 state["tokens_used"]에 누적하고,
    실제 재생성 횟수는 state["retry_count"]에, 이 문항에 재시도·절단이 일어났는지는
    각각 state["actions_retried"]/state["actions_truncated"]에 기록한다 — 평가기가
    actions_retry_rate·actions_truncate_rate를 계산하는 데 쓴다.
    """
    question = state["question"]
    store = state["store"]
    context = state.get("context", {})
    market = context.get("market")
    trend = context.get("trend")
    seasonality = context.get("seasonality")
    base_user_prompt = build_user_prompt(question, store, market, trend, seasonality)
    deadline = state.get("deadline")

    total_tokens = 0
    retry_count = 0
    # 재시도와 절단이 한 문항 안에서 둘 다 일어날 수 있어(드물지만) 문자열 하나로
    # 겹쳐 쓰지 않고 불리언 두 개로 각각 기록한다 — 평가기의 actions_retry_rate·
    # actions_truncate_rate가 서로 독립적인 지표이기 때문이다.
    actions_retried = False
    actions_truncated = False
    # 두 교정 힌트를 독립적으로 누적한다 — reasons 재시도 중 actions 오류가 나는 등
    # 순서가 섞여도(또는 그 반대) 직전에 필요해진 힌트가 빠지지 않아야 한다
    # (Codex 리뷰: 카운터 상태만으로 우선순위를 매기면 이후 actions 힌트가 영영
    # 안 붙는 회귀가 있었음).
    hints: list[str] = []

    while True:
        hint_text = "\n".join(hints)
        user_prompt = base_user_prompt if not hints else f"{base_user_prompt}\n\n{hint_text}"
        raw, tokens = call_llm(SYSTEM_PROMPT, user_prompt, json_mode=True, deadline=deadline)
        total_tokens += tokens

        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError("LLM이 유효한 JSON을 반환하지 않았습니다.") from exc

        summary = parsed.get("summary") if isinstance(parsed, dict) else None
        if not isinstance(summary, str) or not summary.strip():
            raise ValueError("LLM이 빈 전략 요약을 반환했습니다.")

        raw_actions = parsed.get("actions")
        if not isinstance(raw_actions, list):
            # LLM 응답이 계약을 어긴 것이지 우리 코드의 타입 계약 위반이 아니다 —
            # 이 함수의 다른 검증(요약·근거 등)도 전부 ValueError로 통일한다.
            raise ValueError(  # noqa: TRY004
                "LLM이 유효한 actions 배열을 반환하지 않았습니다(actions_not_list)."
            )

        # 개수(절단)를 항목별 형식 검증보다 먼저 처리한다 — 순서를 바꾸면
        # 어차피 버릴 초과 항목(예: 4번째)의 형식 오류가 실제로 쓰일 앞
        # MAX_ACTIONS개까지 실패시킨다(Codex 리뷰).
        raw_actions, truncated_now = _truncate_actions(raw_actions)

        if len(raw_actions) < MIN_ACTIONS:
            if retry_count < _MAX_RETRIES:
                retry_count += 1
                actions_retried = True
                if RETRY_ACTIONS_HINT not in hints:
                    hints.append(RETRY_ACTIONS_HINT)
                continue
            raise ValueError(
                "LLM이 재생성 후에도 actions를 하나도 반환하지 않았습니다(actions_empty)."
            )

        actions, actions_error = _validate_action_items(raw_actions)
        if actions is None:
            raise ValueError(f"LLM이 유효한 actions 배열을 반환하지 않았습니다({actions_error}).")
        if truncated_now:
            actions_truncated = True

        reasons = _parse_reasons(parsed.get("reasons"))
        if reasons is not None:
            break
        if retry_count >= _MAX_RETRIES:
            raise ValueError("LLM이 재생성 후에도 근거(reasons)를 반환하지 않았습니다.")
        retry_count += 1
        if RETRY_REASONS_HINT not in hints:
            hints.append(RETRY_REASONS_HINT)

    title = normalize_title(parsed.get("title"), store["name"])

    # market_for_consult/trend_for_consult가 둘 다 실패(또는 조기 실행)하면 sources가
    # 비어 있는 채로 넘어온다 — 서비스 계약(ConsultantModelResult.sources, min_length=1)이
    # 깨지므로, 최소한 가게 정보는 항상 근거로 쓰이니 "가게정보"를 기본 출처로 채운다.
    # 이미 다른 노드가 채워둔 sources가 있으면(operator.add reducer로 합산되므로)
    # 여기서는 아무것도 반환하지 않아 중복으로 늘어나지 않게 한다.
    sources_update = {} if state.get("sources") else {"sources": ["가게정보"]}

    return {
        "result": {"title": title, "summary": summary.strip(), "actions": actions, "reasons": reasons},
        "tokens_used": state.get("tokens_used", 0) + total_tokens,
        # 다른 노드(D9 strategy_check)도 같은 키에 쓸 예정이라 덮어쓰지 않고 누적한다
        # (PM 리뷰, PR #93).
        "retry_count": state.get("retry_count", 0) + retry_count,
        "actions_retried": actions_retried,
        "actions_truncated": actions_truncated,
        **sources_update,
    }


def _truncate_actions(actions: list) -> tuple[list, bool]:
    """개수가 MAX_ACTIONS를 넘으면 앞에서부터 그만큼만 남기고 잘라낸다(D-139
    후속, PM 승인 — 많이 낸 것이지 답을 못 낸 게 아니므로 LLM 재호출 없이
    바로 복구한다). 항목별 형식 검증(_validate_action_items)보다 반드시
    먼저 호출해야 한다 — 순서를 바꾸면 어차피 버릴 초과 항목의 형식 오류가
    실제로 쓰일 앞 MAX_ACTIONS개까지 실패시킨다(Codex 리뷰)."""
    if len(actions) > MAX_ACTIONS:
        return actions[:MAX_ACTIONS], True
    return actions, False


def _validate_action_items(actions: list) -> tuple[list[dict] | None, str | None]:
    """actions 항목별 형식(API 계약: type 4종 enum, content 1개 이상)을 검증하고
    공백을 정리한 새 리스트를 반환한다 — 반드시 _truncate_actions() 이후,
    개수가 MAX_ACTIONS 이하로 정리된 리스트에 대해서만 호출한다. 형식이 안
    맞으면 (None, 실패 사유)를 반환한다 — 사유를 구분해야 로그만 보고 리스트
    형태·enum·content 중 무엇이 원인인지 알 수 있다(Codex 리뷰: 전부 같은
    메시지로 뭉뚱그려져 있었음)."""
    normalized = []
    for action in actions:
        if not isinstance(action, dict):
            return None, "actions_not_list"
        action_type = action.get("type")
        content = action.get("content")
        if not isinstance(action_type, str) or action_type not in _VALID_ACTION_TYPES:
            return None, "invalid_type"
        if not isinstance(content, str) or not content.strip():
            return None, "missing_content"
        normalized.append({"type": action_type, "content": content.strip()})

    return normalized, None


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
