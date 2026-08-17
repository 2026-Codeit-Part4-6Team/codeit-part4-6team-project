"""
validation/self_check.py
AI 모델 답변 검증 (품질)
"""


def self_check(result: dict, context: dict) -> dict:
    """AI 모델 답변 검증 — 근거 · 완결성 판정

    ※ 현재는 D1 스텁(무조건 통과). D5에 실구현 예정.
    반환 규격:
        action  : "pass" | "warn" | "reject"
        reasons : 실패 사유 목록 (예: ["근거 없음", "제안 개수 부족"])
        message : 사용자 안내
    """
    return {
        "action": "pass",
        "reasons": [],
        "message": "",
    }