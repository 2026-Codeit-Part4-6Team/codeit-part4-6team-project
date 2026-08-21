# models/consult/graph/state.py — 컨설턴트 챗봇 GraphState (CommonState 확장)
from typing import NotRequired

from models.shared.state_common import CommonState


class ConsultState(CommonState):
    """컨설턴트 챗봇 전용 필드. 공통 필드는 CommonState 참고.

    전략 결과는 별도 필드를 만들지 않고 상속받은 result에 담는다.
    result = {"summary": ..., "actions": [...], "reasons": [...]}

    서비스 응답 계약(API/DB Contract v0.3 §6.4, §11.1 확정)은 Basic과 달리 proposals/copy를
    쓰지 않고 strategy(summary, actions[])·reasons[]를 그대로 사용한다. 즉 result를 문자열로
    변환하는 단계 없이 이 구조를 그대로 최종 응답 payload로 조립하면 된다.
    """

    retry_count: NotRequired[int]  # 전략 재시도 누적값(reasons §6.5+actions 합산 최대 2회, actions는 PM 승인 대기)
    suggested_chips: NotRequired[list[str]]  # 추천 질문 칩 3종 (SDP §2.1, D1 회의에서 응답 계약 추가 합의)
    # 그래프 진입 시(security_input) 1회 세팅, 모든 call_llm 호출이 공유하는 절대 마감
    # (time.monotonic() 기준). 안 넘기면 매 call_llm 호출이 각자 새 예산을 받아, strategy의
    # 재시도(최대 3회)+429 백오프가 겹치면 서비스 60초 타임아웃에 근접할 수 있다(D-144, PM 리뷰 PR #93).
    deadline: NotRequired[float]
    # BasicState(models/basic/graph/state.py)와 동일 패턴 — CommonState엔 없어서
    # 검증 노드가 반환해도 LangGraph가 스키마 밖 키로 보고 조용히 버렸다(Codex 리뷰로
    # 발견, assemble_response()의 blocked/error 분기가 항상 무력화되는 치명적 버그였음).
    status: NotRequired[str]  # ok, blocked, error
    issues: NotRequired[
        list[dict]
    ]  # [{"source": ..., "action": "block"/"reask"/"warn", "reason": ..., "message": ...}, ...]
