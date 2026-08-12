"""
validation/self_check.py 
AI 모델 답변 검증 (품질)
"""
    
def self_check(result: dict, context: dict) -> dict:
    """AI 모델 답변 검증 — 근거 · 완결성 판정"""
    return {
        "action": "pass"/"warn"/"reject",
        "reasons": ["근거 없음", "제안 개수 부족"],
        "message": "..."
    }