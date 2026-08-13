"""
validation/regulation.py
규제 준수 검증 (RAG)
"""


def check_regulation(copy: str) -> dict:
    """규제 준수 검증 (RAG) — 1단 키워드 스크리닝 → 2단 legal_kb RAG 판정

    ※ 현재는 D1 스텁(무조건 통과). D4에 실구현 예정.
    반환 규격:
        action      : "pass" | "warn" | "block"
        law         : 근거 조문 (예: "표시광고법 제3조")
        reason      : 왜 안 되는지
        alternative : 대안 문구
        message     : 사용자 안내
    """
    return {
        "action": "pass",
        "law": "",
        "reason": "",
        "alternative": "",
        "message": "",
    }