# models/consult/main.py — 컨설턴트 파이프라인 진입점 + 서비스 응답 조립
"""서비스는 이 모듈의 run() 하나만 호출한다.

그래프 내부 state 구조(result·validation·issues)는 서비스가 알 필요가 없다
(Contract v0.3 §2.2 — Model은 ModelRequest를 받고 ModelResult를 반환한다).
D1+D2에서 "서비스에 응답할 때만 변환한다"로 정했고 D4에 구현할 예정이었으나
누락됐던 부분이다.
"""

import logging

# TODO(D7): PM이 models/shared/llm_errors.py로 이관 예정(PR 진행 중, 2026-08-18).
# 이관 완료되면 아래 import만 models.shared.llm_errors로 바꾸면 된다(로직 변경 없음).
from models.basic.llm import classify_llm_error
from models.consult.graph.build_consultant import build_consultant

# suggested_chips 노드 자신의 폴백을 그대로 재사용한다 — 조립 단계에서 별도
# 문구를 새로 만들면, 폴백이 노드 안/최종 조립 중 어디서 걸리느냐에 따라
# 사용자가 다른 질문을 보게 된다.
from models.consult.nodes.suggested_chips import _FALLBACK_CHIPS

logger = logging.getLogger(__name__)


def run(request: dict) -> dict:
    """ModelRequest dict를 받아 ModelResult dict를 반환한다.

    request 구성이나 그래프 실행, 응답 조립(assemble_response) 중 어디서
    실패하든 서비스에는 항상 계약을 지키는 dict를 돌려준다 — 예외를 그대로
    올리면 서비스가 ModelResult가 아닌 것을 받게 되어 ErrorResult(§6.6)
    계약을 만족할 수 없다.
    """
    try:
        initial_state = {
            "chatbot_type": request["chatbot_type"],
            "user_id": request["user_id"],
            "question": request["question"],
            "store": request["store"],
            "extra": request.get("extra") or {},
            "tokens_used": 0,
        }
        final_state = build_consultant().invoke(initial_state)
        return assemble_response(final_state)
    except Exception as exc:  # noqa: BLE001 — 어떤 실패든 ErrorResult 계약으로 변환한다
        logger.warning("컨설턴트 파이프라인 실행 실패: %s", exc)
        return {
            "status": "error",
            "reason": classify_llm_error(exc),
            "message": "전략 생성 중 오류가 발생했습니다.",
        }


def assemble_response(state: dict) -> dict:
    """최종 state를 서비스 응답 계약으로 변환한다.

    ok      -> ConsultantModelResult
    blocked -> BlockedResult   {status, action, reason, message}
    error   -> ErrorResult     {status, reason, message}  reason은 4종 enum
    """
    status = state.get("status", "ok")
    last_issue = (state.get("issues") or [{}])[-1]

    if status == "blocked":
        return {
            "status": "blocked",
            "action": last_issue.get("action", "block"),
            "reason": last_issue.get("reason", "policy_blocked"),
            # message는 min_length=1이라 빈 문자열이면 계약 위반이다
            "message": last_issue.get("message") or "요청을 처리할 수 없습니다.",
        }

    if status == "error":
        return {
            "status": "error",
            # ErrorResult.reason은 timeout·rate_limit·provider_error·unknown 4종만 허용
            "reason": last_issue.get("reason", "unknown"),
            "message": last_issue.get("message") or "전략 생성 중 오류가 발생했습니다.",
        }

    result = state.get("result") or {}
    if not result.get("summary"):
        # 전략 노드가 안 돌았거나 결과가 비었다 — ok로 내보내면 계약이 깨진다
        logger.warning("전략 결과가 비어 있어 error로 변환합니다.")
        return {
            "status": "error",
            "reason": "unknown",
            "message": "전략을 생성하지 못했습니다.",
        }

    store_name = (state.get("store") or {}).get("name", "우리 가게")
    chips = [
        c for c in (state.get("suggested_chips") or [])
        if isinstance(c, str) and c.strip()
    ]

    return {
        "status": "ok",
        # title은 이력 목록 라벨이라 여기서 실패시키지 않고 폴백한다(D-179)
        "title": (result.get("title") or f"{store_name} 마케팅 전략")[:100],
        # 그래프 state는 평면(summary·actions·reasons)인데, 계약은 strategy로 한 겹 감싼다
        "strategy": {
            "summary": result["summary"],
            "actions": result["actions"],
        },
        "reasons": result["reasons"],
        "sources": state.get("sources") or ["가게정보"],
        "tokens_used": state.get("tokens_used", 0),
        "suggested_chips": chips if len(chips) == 3 else _FALLBACK_CHIPS,
    }
