"""
validation/regulation.py 
규제 준수 검증 (RAG)
"""

def check_regulation(copy: str) -> dict:
    """규제 준수 검증 (RAG) — 1단 키워드 스크리닝 → 2단 legal_kb RAG 판정"""
    return {
        "action": "pass"/"warn"/"block",
        "law": "표시광고법 제3조",                # 근거 조문 (RAG 결과)
        "reason": "객관적 근거 없는 최상급 표현",  # 왜 안 되는지
        "alternative": "정성껏 볶은 원두",        # 대안 문구
        "message": ""                           # 사용자 안내
    }