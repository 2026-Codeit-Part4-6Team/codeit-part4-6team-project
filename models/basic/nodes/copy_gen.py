import json

from models.shared.llm import call_llm
from models.shared.llm_errors import classify_llm_error

from ..config import COPY_MAX_RETRY
from ..graph.state import BasicState

FEWSHOT_TERMS: list[str] = []
FEWSHOT_NUMBERS: list[int] = []

SYSTEM_PROMPT = """너는 소상공인 광고 카피라이터다. 표시광고법을 준수한다.
'최고', '유일', '1등'처럼 근거 없는 과장 표현과 질병 예방·치료 효능 표현은 쓰지 않는다.

준수 사항:
- 가게 이름(store.name)은 주어진 값 그대로 정확히 사용한다. 절대 변형하거나 다르게 쓰지 않는다.
- 한국어로만 작성한다. 영어 단어를 억지로 섞거나, 문맥과 무관한 단어를 넣지 않는다.
- suggested_alternative가 주어지면 그 대안 표현을 최대한 살려서 다시 쓴다.
<<<<<<< HEAD
- consultant_strategy·consultant_reasons가 주어지면, 이건 컨설턴트가 이미 분석해 낸
전략과 그 근거다. 무시하지 말고 카피의 핵심 소재로 우선 반영한다
(예: strategy.actions 의 content를 실제 문구에 녹여내고, reasons를 광고 톤·소구점에 반영).

구체성 원칙 (중요):
- "맛있어요", "지금 만나보세요"처럼 어느 가게에나 붙여도 말이 되는 일반론은 쓰지 않는다.
- trend(검색 트렌드)·extra(강점·가격대·타겟 등) 중 값이 채워진 항목이 있으면,
  최소 1가지 이상을 카피 문장 안에 구체적으로 녹여 쓴다. 값이 없는 항목은 언급하지 않는다.
- 제공된 정보에 없는 사실(가격, 원산지, 수상 이력 등)은 절대 지어내지 않는다 — 구체성은
  "있는 정보를 구체적으로" 쓰는 것이지 "없는 정보를 만들어내는" 것이 아니다.
- market(상권 정보)은 구체성 확보 목적으로 쓰지 않는다. 매장 수·거리 등 market에서 나온
  수치나 "경쟁 매장보다/와는 다른" 같은 비교 표현은 카피에 절대 언급하지 않는다.

예시(참고용, 그대로 베끼지 말 것):
- 일반론(피할 것): "신메뉴 출시! 지금 만나보세요"
- 구체적(지향할 것): "역삼동 직장인들 사이 콜드브루 검색이 늘고 있어요 — 당일 로스팅 원두로 내린 카페 코드잇 아이스 아메리카노"
=======
- consultant_strategy·consultant_reasons가 주어지면, 이건 컨설턴트가 이미 분석해 낸 
전략과 그 근거다. 무시하지 말고 카피의 핵심 소재로 우선 반영한다
(예: strategy.actions 의 content를 실제 문구에 녹여내고, reasons를 광고 톤·소구점에 반영).
>>>>>>> c2856af92160077083cc6d1b366cba79f23d3676

채널별 규칙:
- instagram: 짧고 친근한 문장 + 해시태그 3~5개 + 이모지
- xbanner: 세로형 스탠드 배너 상단에 들어갈 한 줄, 눈에 띄는 핵심 메시지

주어진 정보를 참고해 서로 톤이 다른 광고 카피 3안을 만든다.
다음 JSON 형식으로만 답한다:
{"candidates": ["카피1", "카피2", "카피3"]}
"""

_NUM_CANDIDATES = 3


def copy_gen_node(state: BasicState) -> dict:
    """수집된 컨텍스트(상권/트렌드/벤치마크)와 규제 검수 결과를 바탕으로
    LLM을 호출해 톤이 다른 광고 카피 3안을 생성한다. 파싱에 실패한 후보는
    개별 에러로 표시하고, 전체 실패 시 재시도 카운트를 올린다.

    source_context가 있으면 컨설팅→광고 연계 요청이다 — 컨설턴트가
    이미 낸 전략(strategy)·근거(reasons)를 프롬프트에 실어 카피에 반영하고,
    컨설턴트 쪽 근거 출처(sources)도 최종 응답의 sources에 합친다.
    """
    context_data = state.get("context") or {}
    source_context = state.get("source_context")

    payload = {
        "question": state["question"],
        "platform": state["platform"],
        "store": state["store"],
        "extra": state.get("extra") or {},
        "market": context_data.get("market"),
        "trend": context_data.get("trend"),
        "benchmark": context_data.get("benchmark"),
    }
    if source_context:
        payload["consultant_strategy"] = source_context.get("strategy")
        payload["consultant_reasons"] = source_context.get("reasons")

    regulation_result = (state.get("validation") or {}).get("regulation")
    if regulation_result and regulation_result.get("action") in ("block", "warn"):
        payload["avoid"] = regulation_result.get("message")
        alternative = regulation_result.get("alternative")
        if alternative:
            payload["suggested_alternative"] = alternative

    source_context = state.get("source_context")
    if source_context:
        strategy = source_context["strategy"]
        actions = " / ".join(a["content"] for a in strategy["actions"])
        payload["consulting_strategy"] = {
            "summary": strategy["summary"],
            "actions": actions,
            "reasons": " · ".join(source_context["reasons"]),
        }

    try:
        raw, tokens = call_llm(
            SYSTEM_PROMPT,
            json.dumps(payload, ensure_ascii=False),
            json_mode=True,
            deadline=state.get("deadline"),
        )
    # BLE001 억제 사유: call_llm의 모든 실패(429/timeout/기타 API 오류)를 잡아 status=error로 안전하게 전환하기 위해 의도적으로 넓게 잡음
    except Exception as exc:  # noqa: BLE001
        return {
            "status": "error",
            "issues": state.get("issues", [])
            + [
                {
                    "source": "copy_gen",
                    "reason": classify_llm_error(exc),
                    "message": "카피 생성 중 오류가 발생했습니다.",
                }
            ],
        }
    parsed_copies = _parse_candidates(raw)

    candidates = []
    for copy_text in parsed_copies:
        if copy_text is not None:
            candidates.append({"copy": copy_text})
        else:
            candidates.append(
                {
                    "copy": None,
                    "image_b64": None,
                    "error": {
                        "field": "copy",
                        "reason": "parse_failed",
                        "message": "카피 생성에 실패했습니다.",
                    },
                }
            )

    updates = {
        "copy_candidates": candidates,
        "tokens_used": state.get("tokens_used", 0) + tokens,
    }
<<<<<<< HEAD
    if source_context:
        updates["sources"] = ["컨설팅 전략"]
=======
    if source_context and source_context.get("sources"):
        updates["sources"] = source_context["sources"]
>>>>>>> c2856af92160077083cc6d1b366cba79f23d3676

    all_failed = all(c["copy"] is None for c in candidates)
    if all_failed:
        retry_count = state.get("copy_retry_count", 0) + 1
        updates["copy_retry_count"] = retry_count
        if retry_count >= COPY_MAX_RETRY:
            updates["status"] = "error"
            updates["issues"] = state.get("issues", []) + [
                {
                    "source": "copy_gen",
                    "reason": "copy_generation_failed",
                    "message": "카피 생성에 반복적으로 실패했습니다.",
                }
            ]

    return updates


def _parse_candidates(raw: str) -> list[str | None]:
    """JSON을 파싱해 카피 후보 3개를 문자열만 남기고 반환한다.

    _parse_chips(models/consult/nodes/suggested_chips.py)와 같은 3단계로 검증한다:
    JSONDecodeError → dict 여부 → 각 항목이 비어있지 않은 str인지.
    파싱 실패나 타입이 안 맞는 항목은 None으로 표시해 호출부가 개별
    parse_failed 에러로 처리하게 한다 — 숫자·객체 등이 카피로 새는 걸 막는다.
    """
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return [None] * _NUM_CANDIDATES

    if not isinstance(parsed, dict):
        return [None] * _NUM_CANDIDATES

    raw_candidates = parsed.get("candidates")
    if not isinstance(raw_candidates, list):
        return [None] * _NUM_CANDIDATES

    result: list[str | None] = []
    for i in range(_NUM_CANDIDATES):
        item = raw_candidates[i] if i < len(raw_candidates) else None
        if isinstance(item, str) and item.strip():
            result.append(item.strip())
        else:
            result.append(None)
    return result
