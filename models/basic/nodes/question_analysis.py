import json

from models.shared.llm import call_llm
from models.shared.llm_errors import classify_llm_error

from ..graph.state import BasicState

SYSTEM_PROMPT = """너는 소상공인 광고 카피 요청을 분석하는 어시스턴트다.
사용자 질문과 가게 정보를 보고 두 가지를 판단한다.
1) question·extra·consultant_strategy·consultant_reasons(주어진 경우)를 모두
   참고해 질문을 광고 카피 생성에 바로 쓸 수 있도록 구체적으로 재작성한다.
2) 카피를 만들기에 정보가 충분한지 판단한다.
3) 검색 트렌드 조회에 쓸 핵심 키워드를 뽑는다.

모든 출력(rewritten_question, message)은 한국어로만 작성한다. 다른 언어 문자를
섞지 않는다.

판단 기준 (기본값은 "충분함"이다 — 애매하면 충분하다고 판단한다):
- question이 "무엇을 홍보/판매하는 것에 대한 것인지" 주제나 카테고리를 하나라도
  담고 있으면 충분하다고 판단한다. 구체적인 메뉴명·가격·특징까지 없어도 된다.
  예: "여름 신메뉴 홍보 문구 만들어줘" → 충분함 (신메뉴라는 주제가 있음)
  예: "이벤트 홍보 문구 만들어줘" → 충분함 (이벤트라는 주제가 있음)
- extra에 이미 채워진 정보(목적/가격대/고객층/특장점, 되물음에 대한 답변 등)가
  하나라도 있으면 그 자체로 충분한 것으로 간주한다. 더 자세한 내용을 추가로
  요구하지 않는다.
- consultant_strategy·consultant_reasons가 주어지면(컨설팅→광고 연계 요청),
  question을 재작성할 때 strategy.actions의 구체적 실행 항목과 reasons를
  적극 반영해 구체적으로 다시 쓴다. 이 정보가 있는 것만으로도 그 자체로
  충분한 것으로 간주한다.
- question·extra·consultant_strategy·consultant_reasons를 전부 합쳐도
  "무엇에 대한 광고인지" 주제조차 짐작할 수 없을 때만(예: "광고 만들어줘",
  "문구 좀 써줘") 정보 부족으로 판단한다.
- 판단이 애매하면 무조건 충분함(sufficient: true)으로 판단한다. 정보 부족
  판단은 최후의 수단이다.

정보가 부족할 때 message는:
- 정형화된 문구를 그대로 쓰지 말고, 사용자의 question에 이미 담긴 단서를 살려서
  구체적으로 되묻는 자연스러운 한 문장으로 작성한다.

keyword는:
- 질문에서 상품·메뉴·주제를 나타내는 명사구를 1~3단어의 검색어 형태로 뽑는다
  (문장이 아니라 실제 검색창에 입력할 법한 짧은 검색어처럼 작성한다).
  예: "여름 신메뉴 홍보 문구 만들어줘" → keyword: "여름 신메뉴"
  예: "아이스 아메리카노 신메뉴 홍보" → keyword: "아이스 아메리카노"
- 정보가 부족해도 짐작 가능한 범위에서 keyword는 최대한 채운다. 정말 아무
  단서도 없으면 빈 문자열로 둔다.

다음 JSON 형식으로만 답한다:
{"sufficient": true/false, "rewritten_question": "...", "keyword": "...", "message": "..."}
"""


def question_analysis_node(state: BasicState) -> dict:
    """LLM으로 질문과 가게 정보를 분석해 카피 생성에 쓸 질문을 재작성하고,
    정보가 부족하면 되묻기(reask) 상태로 전환한다."""
    context = {
        "question": state["question"],
        "store": state["store"],
        "extra": state.get("extra") or {},
    }
    source_context = state.get("source_context")
    if source_context:
        context["consultant_strategy"] = source_context.get("strategy")
        context["consultant_reasons"] = source_context.get("reasons")

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
                    "source": "question_analysis",
                    "reason": classify_llm_error(exc),
                    "message": "질문 분석 중 오류가 발생했습니다.",
                }
            ],
        }
    parsed = json.loads(raw)
    tokens_used = state.get("tokens_used", 0) + tokens

    if not parsed.get("sufficient", True):
        return {
            "status": "blocked",
            "tokens_used": tokens_used,
            "issues": state.get("issues", [])
            + [
                {
                    "source": "question_analysis",
                    "action": "reask",
                    "reason": "insufficient_info",
                    "message": parsed.get(
                        "message", "무엇을 광고하시는지 조금 더 알려주세요."
                    ),
                }
            ],
        }

    return {
        "status": "ok",
        "question": parsed.get("rewritten_question", state["question"]),
        "keyword": parsed.get("keyword")
        or parsed.get("rewritten_question", state["question"]),
    }
