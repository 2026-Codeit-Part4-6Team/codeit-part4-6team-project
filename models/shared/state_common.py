# graph/state_common.py — PM 제시 공통 뼈대 (두 챗봇 공유)
import operator
from typing import Annotated, Literal, NotRequired, TypedDict


class StoreInfo(TypedDict):
    """가게 정보 — 서비스 담당이 요청 JSON에 실어 보냄"""

    name: str  # "카페 코드잇"
    type: str  # "카페"
    address: str  # "서울 강남구 역삼동"
    lat: float  # 37.5
    lng: float  # 127.0


def merge_dicts(left: dict, right: dict) -> dict:
    """병렬 노드가 각자 다른 키를 채워도 값이 유지되도록 얕은 병합하는 reducer."""
    return {**left, **right}


class CommonState(TypedDict):
    # ── 입력 (서비스 담당에게서 받음, 최초 요청에 항상 존재) ──
    chatbot_type: Literal["basic", "consultant"]
    user_id: int
    question: str
    store: StoreInfo

    # ── 입력 (선택) — 서비스 개발 D1 계약 문서 §3.5 기준. Basic은 platform 필수,
    #    Consultant는 생략 가능하다고 D1 회의에서 확정.
    #    Basic 필수 여부는 여기서 강제하지 않는다 — TypedDict는 런타임 검증이 안 되므로
    #    서비스 계층의 Pydantic 요청 모델(ModelRequest)에서 검증하는 게 맞다(StoreInfo와 동일 원칙) ──
    platform: NotRequired[str | None]  # "instagram" 등, Consultant는 보통 None
    extra: NotRequired[dict]  # 확장 조건(목적·가격대 등)

    # ── 컨텍스트 (병렬 조회 노드가 채움 — 같은 키를 동시에 갱신하므로 reducer 필요) ──
    context: NotRequired[Annotated[dict, merge_dicts]]  # {"market": {...}, "trend": {...}}

    # ── 출력 (파이프라인 진행 중 채워짐) ──
    result: NotRequired[dict]  # 챗봇별 결과 (basic=proposals / consultant=strategy)
    sources: NotRequired[Annotated[list[str], operator.add]]  # ["상권분석", "트렌드"]
    tokens_used: NotRequired[int]

    # ── 검증 (병렬 판정 노드가 채움 — 같은 키를 동시에 갱신하므로 reducer 필요) ──
    validation: NotRequired[Annotated[dict, merge_dicts]]  # {"input": {...}, "regulation": {...}}

    # ── 광고 연계 (v10 확정) ──
    source_gen_id: NotRequired[int | None]  # 컨설팅→광고 파생 추적
    source_context: NotRequired[dict | None]  # 검증된 컨설팅 전략 원문
