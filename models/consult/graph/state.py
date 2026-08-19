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

    retry_count: NotRequired[int]  # 근거 부족 재생성 루프 카운터 (SDP §6.5, 최대 2회)
    suggested_chips: NotRequired[list[str]]  # 추천 질문 칩 3종 (SDP §2.1, D1 회의에서 응답 계약 추가 합의)
    # 그래프 진입 시(security_input) 1회 세팅, 모든 call_llm 호출이 공유하는 절대 마감
    # (time.monotonic() 기준). 안 넘기면 매 call_llm 호출이 각자 새 예산을 받아, strategy의
    # 재시도(최대 3회)+429 백오프가 겹치면 서비스 60초 타임아웃에 근접할 수 있다(D-052, PM 리뷰 PR #93).
    deadline: NotRequired[float]
