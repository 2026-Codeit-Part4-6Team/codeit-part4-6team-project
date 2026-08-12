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
    return any(isinstance(name, str) and industry in name for name in names)


def _valid_coord(value: object) -> bool:
    """거리 계산에 쓸 수 있는 좌표 값인지 확인한다(bool 제외 유한한 숫자만 허용).

    stores는 캐시(사용자가 손상시킬 수 있는 JSON)와 실시간 API 응답 양쪽에서 오므로,
    이 지점에서 걸러야 두 경로 모두 haversine의 예외를 예방할 수 있다. 값 종류를 나열해서
    막는 대신 변환·검사 자체를 try/except로 감싼다 — float() 표현 범위를 벗어난 거대한
    정수 등 예상 못 한 입력이 와도 예외 종류를 계속 추가할 필요 없이 전부 "무효"로 처리된다.
    """
    if isinstance(value, bool):
        return False
    try:
        return isinstance(value, (int, float)) and math.isfinite(float(value))
    except (OverflowError, ValueError):
        return False


def aggregate(
    stores: list[dict], total_count: int, industry: str | None, lat: float, lng: float
) -> dict:
    """반경내 상가업소 목록에서 계약 형식(docs/repo_contract.md)을 계산한다.

    TODO: numOfRows(최대 1000)를 넘는 매장은 stores에 담기지 않으므로,
    same_industry_count/nearest_distance_m/industry_breakdown은 첫 페이지까지만 집계된다.
    total_count는 API의 totalCount를 그대로 쓰므로 이 한계와 무관하게 정확하다.
    """
    # dict가 아닌 요소(손상된 캐시, 예상 밖 API 응답 등)는 이후 모든 처리에서 안전하도록 여기서 제외한다.
    stores = [store for store in stores if isinstance(store, dict)]

    industry_breakdown: dict[str, int] = {}
    for store in stores:
        name = store.get("indsMclsNm")
        if isinstance(name, str) and name:
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
        if _valid_coord(store.get("lat")) and _valid_coord(store.get("lon"))
    ]
    nearest = round(min(distances)) if distances else None

    return {
        "total_count": total_count,
        "same_industry_count": len(matches),
        "nearest_distance_m": nearest,
        "industry_breakdown": industry_breakdown,
    }


def fetch_raw(lat: float, lng: float, radius: int = 500) -> tuple[list[dict], int] | None:
    """상권정보 OpenAPI(반경내 상가업소 조회)를 호출해 원본 매장 목록·전체 매장 수를 반환한다.

    업종 집계 없이 원본만 반환한다 — market_repo가 이 결과를 업종과 무관하게 캐싱하고,
    aggregate()는 조회할 때마다 별도로 호출하기 위함(같은 좌표라도 industry가 다르면
    캐시를 재사용해야 하므로). 실패 시 None.

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

    return stores, total_count


def fetch(lat: float, lng: float, radius: int = 500, industry: str | None = None) -> dict | None:
    """상권정보 OpenAPI를 호출해 계약 형식(docs/repo_contract.md)으로 변환한다. 실패 시 None."""
    fetched = fetch_raw(lat, lng, radius)
    if fetched is None:
        return None

    stores, total_count = fetched
    return aggregate(stores, total_count, industry, lat, lng)
