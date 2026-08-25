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

채널별 규칙:
- instagram: 짧고 친근한 문장 + 해시태그 3~5개 + 이모지
- xbanner: 세로형 스탠드 배너 상단에 들어갈 한 줄, 눈에 띄는 핵심 메시지

주어진 정보를 참고해 서로 톤이 다른 광고 카피 3안을 만든다.
다음 JSON 형식으로만 답한다:
{"candidates": ["카피1", "카피2", "카피3"]}
"""


def copy_gen_node(state: BasicState) -> dict:
    """수집된 컨텍스트(상권/트렌드/벤치마크)와 규제 검수 결과를 바탕으로
    LLM을 호출해 톤이 다른 광고 카피 3안을 생성한다. 파싱에 실패한 후보는
    개별 에러로 표시하고, 전체 실패 시 재시도 카운트를 올린다."""
    context_data = state.get("context") or {}
    payload = {
        "question": state["question"],
        "platform": state["platform"],
        "store": state["store"],
        "extra": state.get("extra") or {},
        "market": context_data.get("market"),
        "trend": context_data.get("trend"),
        "benchmark": context_data.get("benchmark"),
    }

    source_context = state.get("source_context")
    if source_context:
        strategy = source_context.get("strategy") or {}
        actions = strategy.get("actions") or []
        payload["source_context"] = {
            "summary": strategy.get("summary", ""),
            "actions": " / ".join(
                action.get("content", "")
                for action in actions
                if action.get("content")
            ),
            "reasons": " · ".join(source_context.get("reasons") or []),
        }

    regulation_result = (state.get("validation") or {}).get("regulation")
    if regulation_result and regulation_result.get("action") in ("block", "warn"):
        payload["avoid"] = regulation_result.get("message")

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
    parsed = json.loads(raw)
    raw_candidates = parsed.get("candidates", [])

    candidates = []
    for i in range(3):
        if i < len(raw_candidates) and raw_candidates[i]:
            candidates.append({"copy": raw_candidates[i]})
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
