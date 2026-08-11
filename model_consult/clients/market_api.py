# model_consult/clients/market_api.py — 소상공인시장진흥공단 상권정보 OpenAPI 클라이언트
import math
import os

import httpx

_BASE_URL = "https://apis.data.go.kr/B553077/api/open/sdsc2/storeListInRadius"
_EARTH_RADIUS_M = 6371000


def _haversine_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """두 좌표 사이의 거리를 미터 단위로 계산한다."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlambda / 2) ** 2
    return 2 * _EARTH_RADIUS_M * math.asin(math.sqrt(a))


def _matches_industry(store: dict, industry: str) -> bool:
    """업종 대/중/소분류명 중 하나라도 industry 문자열을 포함하면 동일 업종으로 본다.

    TODO(2안): indsLclsCd/indsMclsCd/indsSclsCd 코드 매핑으로 정확도를 높일 수 있다
    (업종 대/중/소분류 조회 오퍼레이션 largeUpjongList 등 필요, 지금은 텍스트 매칭만 사용).
    """
    names = (store.get("indsLclsNm"), store.get("indsMclsNm"), store.get("indsSclsNm"))
    return any(name and industry in name for name in names)


def aggregate(
    stores: list[dict], total_count: int, industry: str | None, lat: float, lng: float
) -> dict:
    """반경내 상가업소 목록에서 계약 형식(docs/repo_contract.md)을 계산한다.

    TODO: numOfRows(최대 1000)를 넘는 매장은 stores에 담기지 않으므로,
    same_industry_count/nearest_distance_m/industry_breakdown은 첫 페이지까지만 집계된다.
    total_count는 API의 totalCount를 그대로 쓰므로 이 한계와 무관하게 정확하다.
    """
    industry_breakdown: dict[str, int] = {}
    for store in stores:
        name = store.get("indsMclsNm")
        if name:
            industry_breakdown[name] = industry_breakdown.get(name, 0) + 1

    if industry is None:
        return {
            "total_count": total_count,
            "same_industry_count": None,
            "nearest_distance_m": None,
            "industry_breakdown": industry_breakdown,
        }

    matches = [store for store in stores if _matches_industry(store, industry)]
    if not matches:
        return {
            "total_count": total_count,
            "same_industry_count": 0,
            "nearest_distance_m": None,
            "industry_breakdown": industry_breakdown,
        }

    distances = [
        _haversine_m(lat, lng, store["lat"], store["lon"])
        for store in matches
        if store.get("lat") is not None and store.get("lon") is not None
    ]
    nearest = round(min(distances)) if distances else None

    return {
        "total_count": total_count,
        "same_industry_count": len(matches),
        "nearest_distance_m": nearest,
        "industry_breakdown": industry_breakdown,
    }


def fetch(lat: float, lng: float, radius: int = 500, industry: str | None = None) -> dict | None:
    """상권정보 OpenAPI(반경내 상가업소 조회)를 호출해 계약 형식으로 변환한다. 실패 시 None.

    MARKET_API_KEY는 디코딩 키를 쓴다 — httpx의 params=가 자동으로 URL 인코딩하므로,
    인코딩 키를 넣으면 이중 인코딩되어 인증에 실패한다.
    """
    api_key = os.getenv("MARKET_API_KEY")
    if not api_key:
        return None

    params = {
        "serviceKey": api_key,
        "radius": radius,
        "cx": lng,
        "cy": lat,
        "numOfRows": 1000,
        "pageNo": 1,
        "type": "json",
    }

    try:
        response = httpx.get(_BASE_URL, params=params, timeout=10.0)
        response.raise_for_status()
        payload = response.json()
    except (httpx.HTTPError, ValueError):
        # ValueError: HTTP 200이어도 인증 실패 등으로 JSON이 아닌 본문(XML/텍스트)이 올 수 있음
        return None

    if payload.get("header", {}).get("resultCode") != "00":
        # API가 HTTP 200으로 오류를 반환하는 경우(예: 인증키 오류) — 정상 데이터로 오인하지 않는다
        return None

    # JSON 응답은 XML 문서의 <response> 래퍼 없이 {"header":..., "body":...}로 온다(실측 확인).
    body = payload.get("body", {})
    items = body.get("items") or []
    item = items.get("item", []) if isinstance(items, dict) else items
    stores = [item] if isinstance(item, dict) else item
    total_count = int(body.get("totalCount", len(stores)))

    return aggregate(stores, total_count, industry, lat, lng)
