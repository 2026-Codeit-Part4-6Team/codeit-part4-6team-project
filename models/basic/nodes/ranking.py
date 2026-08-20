import json

from models.shared.llm import call_llm

from ..graph.state import BasicState
from ..llm_errors import classify_llm_error

SYSTEM_PROMPT = """너는 광고 카피 심사위원(LLM Judge)이다.
아래 후보 카피들을 요청 반영도·구체성·규제 안전성 기준으로 1~5점씩 평가하고,
총점이 높은 순으로 정렬한다. 후보는 0부터 시작하는 index로 참조하며, 개수는
그대로 유지한다(줄이거나 늘리지 않는다).

다음 JSON 형식으로만 답한다:
{"ranked": [{"index": 0, "score": 4.3}, ...]}
"""


def ranking_node(state: BasicState) -> dict:
    """LLM Judge로 카피 후보들을 요청 반영도·구체성·규제 안전성 기준으로
    채점해 점수 높은 순으로 정렬한다. 생성 실패 후보는 그대로 뒤에 붙인다."""
    candidates = state["copy_candidates"]
    valid = [c for c in candidates if c.get("copy")]
    failed = [c for c in candidates if not c.get("copy")]

    if not valid:
        return {"ranked_copies": failed}

    context = {
        "question": state["question"],
        "candidate": [c["copy"] for c in valid],
    }

    try:
        raw, tokens = call_llm(
            SYSTEM_PROMPT,
            json.dumps(context, ensure_ascii=False),
            json_mode=True,
            deadline=state.get("deadline"),
        )
    # BLE001 억제 사유: call_llm의 모든 실패를 잡아 status=error로 안전하게 전환
    except Exception as exc:  # noqa: BLE001
        return {
            "status": "error",
            "issues": state.get("issues", [])
            + [
                {
                    "source": "ranking",
                    "reason": classify_llm_error(exc),
                    "message": "카피 랭킹 중 오류가 발생했습니다.",
                }
            ],
        }
    parsed = json.loads(raw)

    ranked = []
    seen = set()
    for item in parsed.get("ranked", []):
        idx = item.get("index")
        if not isinstance(idx, int) or not (0 <= idx < len(valid)) or idx in seen:
            continue
        seen.add(idx)
        ranked.append({"copy": valid[idx]["copy"], "score": item.get("score")})

    for i, c in enumerate(valid):
        if i not in seen:
            ranked.append({"copy": c["copy"], "score": None})

    return {
        "ranked_copies": ranked + failed,
        "tokens_used": state.get("tokens_used", 0) + tokens,
    }
