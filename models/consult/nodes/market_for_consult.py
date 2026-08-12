# 상권·경쟁 밀도 분석 노드 (3층, 컨설팅용 해석)
from cache.market_repo import get_market
from models.consult.graph.state import ConsultState


def market_for_consult(state: ConsultState) -> dict:
    """get_market() 원본 결과를 컨설팅 관점의 근사 등급(density_tier)으로 해석한다.

    get_market()이 실패(None)하면 그대로 context["market"] = None을 반환한다 —
    상권 데이터 없이도 다른 데이터로 상담을 이어갈 수 있게 하는 부분 성공 허용 원칙.
    """
    store = state["store"]
    market = get_market(store["lat"], store["lng"], industry=store["type"])

    if market is None:
        return {"context": {"market": None}}

    return {
        "context": {
            "market": {**market, "density_tier": _density_tier(market["same_industry_count"])}
        }
    }


def _density_tier(same_industry_count: int | None) -> str:
    """절대 매장 수 기준 근사 등급이다 — 비교할 지역 분포 데이터가 없어 "상위 n%" 같은
    실제 순위·백분위는 계산하지 않는다. 반경 내 매장 목록에 사용자 본인 가게가 포함될
    수 있어 "경쟁사 수"가 아니라 "동일 업종 매장 밀도"로 해석한다.

    TODO: 경계값(1~3/4~8/9+)은 브레인스토밍 때 정한 임의 근사치다. 웹 검색으로 참고할
    만한 공개 통계를 찾아봤으나(4·5호선 역세권 500m 카페 평균 약 68~69개) 업종 분류
    기준과 집계 방식이 우리 API(소상공인시장진흥공단)와 달라 직접 비교할 수 없었다.
    나중에 여유가 되면 우리 API로 여러 지역을 직접 샘플링해 분포를 만들고 이 경계값을
    재조정할 것.
    """
    if same_industry_count is None:
        return "판단 불가"
    if same_industry_count == 0:
        return "경쟁 없음"
    if same_industry_count <= 3:
        return "낮음"
    if same_industry_count <= 8:
        return "보통"
    return "높음"
