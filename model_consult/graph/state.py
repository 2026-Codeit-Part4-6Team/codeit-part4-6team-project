# model_consult/graph/state.py — 컨설턴트 챗봇 GraphState (CommonState 확장)
from typing import NotRequired

from graph.state_common import CommonState


class ConsultState(CommonState):
    """컨설턴트 챗봇 전용 필드. 공통 필드는 CommonState 참고.

    전략 결과는 별도 필드를 만들지 않고 상속받은 result에 담는다(내부용, 구조화 유지).
    result = {"summary": ..., "actions": [...], "reasons": [...]}

    서비스 응답 계약(D1 회의 확정)은 Basic과 동일 envelope를 쓰고 proposals[0].copy에
    텍스트로 풀어서 담는다. result → copy 변환은 D4(전략 제안 노드)에서 처리하며,
    이 파일의 result 구조 자체는 바뀌지 않는다.
    """

    retry_count: NotRequired[int]  # 근거 부족 재생성 루프 카운터 (SDP §6.5, 최대 2회)
    suggested_chips: NotRequired[list[str]]  # 추천 질문 칩 3종 (SDP §2.1, D1 회의에서 응답 계약 추가 합의)
