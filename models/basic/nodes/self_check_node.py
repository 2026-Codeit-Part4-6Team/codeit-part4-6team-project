import logging

from validation.self_check import self_check

from ..config import SELF_CHECK_MAX_RETRY
from ..graph.state import BasicState

logger = logging.getLogger(__name__)


def self_check_node(state: BasicState) -> dict:
    """최종 응답 결과가 요청 맥락에 부합하는지 자가 점검한다.

    reject는 self_check_retry_count로 재시도한다(D-156) — copy_retry_count와
    공유하면 규제 재생성이 예산을 소진해 self_check 재시도 기회가 사라진다.
    상한 초과 시 reason은 계약 enum 밖이라 "unknown"으로 내보낸다(D-157).

    warn(카피 개수 부족·길이 미달·중복 등 품질 경고)은 차단하지 않는다 —
    §6.2 같은 명시적 재생성 요구가 없어 로그만 남긴다.
    """
    result_payload = state.get("result") or {}
    context = state.get("context") or {}

    outcome = self_check(result_payload, context)
    validation = {**state.get("validation", {}), "self_check": outcome}

    updates = {"validation": validation}
    if outcome.get("action") == "warn":
        logger.warning(
            "self_check warn — reasons=%s message=%s",
            outcome.get("reasons"),
            outcome.get("message"),
        )

    if outcome.get("action") == "reject":
        retry_count = state.get("self_check_retry_count", 0) + 1
        updates["self_check_retry_count"] = retry_count
        if retry_count >= SELF_CHECK_MAX_RETRY:
            updates["status"] = "blocked"
            updates["issues"] = state.get("issues", []) + [
                {
                    "source": "self_check",
                    "action": "block",
                    "reason": "unknown",
                    "message": outcome.get("message")
                    or "생성 결과 검증에 실패했습니다.",
                }
            ]

    return updates
