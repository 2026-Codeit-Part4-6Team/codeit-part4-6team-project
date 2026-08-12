"""
validation/security.py
보안 - 2종(입력 검증, 출력 검증 - 같은 성격이라 한 파일에 같이 구현)
"""

def check_input(text: str) -> dict:
    """보안1 — D2에 실구현 예정"""
    return {"action": "pass", "message": ""}

def check_output(text: str) -> dict:
    """보안2 — D4에 실구현 예정"""
    return {"action": "pass", "message": ""}

# 아래 주석친 코드 필요 시 참고(2026.08.12 minjae)
# def check_input(text: str) -> dict:
#     """보안1: 입력 검증 (불법 키워드 · 프롬프트 인젝션 대표 패턴)"""
#     return {"action": "pass"/"warn"/"block", "message": "..."}

# def check_output(text: str) -> dict:
#     """보안2: 출력 검증 (민감정보 · 신상 · 시스템 프롬프트 누출)"""
#     return {"action": "pass"/"warn"/"block", "message": "..."}