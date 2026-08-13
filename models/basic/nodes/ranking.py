import json

from ..graph.state import BasicState
from ..llm import call_llm

SYSTEM_PROMPT = """너는 광고 카피 심사위원(LLM Judge)이다.
아래 후보 카피들을 요청 반영도·구체성·규제 안전성 기준으로 1~5점씩 평가하고,
총점이 높은 순으로 정렬한다. 후보 개수는 그대로 유지한다(줄이지 않는다).

다음 JSON 형식으로만 답한다:
{"ranked": [{"copy": "...", "score": 4.3}, ...]}
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

    raw, tokens = call_llm(
        system=SYSTEM_PROMPT,
        user=json.dumps(context, ensure_ascii=False),
        json_mode=True,
    )
    parsed = json.loads(raw)

    return {
        "ranked_copies": parsed["ranked"] + failed,
        "tokens_used": state.get("tokens_used", 0) + tokens,
    }
