# 시즌·수요 타이밍 노드 (3층, 컨설팅용 해석)
from cache.trend_repo import get_trend
from models.consult.graph.state import ConsultState


def trend_for_consult(state: ConsultState) -> dict:
    """get_trend() 결과를 그대로 컨텍스트에 담는다(market_for_consult와 달리 등급으로
    가공하지 않는다 — direction/related 자체가 이미 컨설팅에 쓸 수 있는 형태이고,
    근거 없는 등급을 만들면 전략 노드가 그 등급을 지어낸 근거처럼 쓸 위험이 있다).

    keyword(question_analysis가 추출, D-079)가 없으면 조회할 대상이 없으므로 API를
    부르지 않고 바로 None을 반환한다. get_trend()가 실패(None)해도 마찬가지로
    None을 반환한다 — 트렌드 데이터 없이도 다른 데이터로 상담을 이어갈 수 있게
    하는 부분 성공 허용 원칙(market_for_consult와 동일).
    """
    keyword = state.get("context", {}).get("question_analysis", {}).get("keyword")
    if keyword is None:
        return {"context": {"trend": None}}

    store = state["store"]
    trend = get_trend(keyword, industry=store["type"])

    return {"context": {"trend": trend}}
