# 계절성 힌트 노드 (3층, 컨설팅용 해석) — 날씨 API 대신 날짜 기반 힌트를 계산한다
from models.consult.graph.state import ConsultState
from models.shared.seasonality import compute_seasonality


def seasonality_for_consult(state: ConsultState) -> dict:
    """요청 시점(또는 VALIDATION_REFERENCE_DATE로 고정된 기준일)의 계절성 힌트를
    context["seasonality"]에 담는다.

    market_for_consult·trend_for_consult와 달리 State에서 아무 값도 읽지 않는다 —
    외부 API·LLM 호출이 전혀 없는 순수 계산이라 실패할 일이 없고, 그만큼 응답시간에도
    사실상 영향을 주지 않는다. sources에도 추가하지 않는다 — 계절성은 상권·트렌드처럼
    외부 데이터 출처가 아니라 요청일에서 계산한 내부 힌트이기 때문이다.
    """
    return {"context": {"seasonality": compute_seasonality()}}
