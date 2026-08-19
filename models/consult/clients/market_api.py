# models/consult/clients/market_api.py — 소상공인시장진흥공단 상권정보 OpenAPI 클라이언트
import json
import math
import os
from pathlib import Path

import httpx

_BASE_URL = "https://apis.data.go.kr/B553077/api/open/sdsc2/storeListInRadius"
_EARTH_RADIUS_M = 6371000
_INDUSTRY_CODE_MAP_PATH = Path(__file__).resolve().parents[3] / "shared_data" / "industry_code_map.json"


def _load_industry_code_map() -> dict[str, str]:
    """D-043 단일 소스(shared_data/industry_code_map.json)를 읽는다.

    파일이 없거나 손상됐어도 예외를 내지 않고 빈 매핑으로 대체한다 — 매핑이 없는
    업종은 어차피 텍스트 매칭으로 폴백하므로(D-041), 이 파일의 문제로 상권 조회
    자체가 죽으면 안 된다.
    """
    try:
        with open(_INDUSTRY_CODE_MAP_PATH, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(data, dict):
        return {}
    return {
        key: value
        for key, value in data.items()
        if isinstance(key, str) and isinstance(value, str) and not key.startswith("_")
    }


_INDUSTRY_CODE_MAP = _load_industry_code_map()


def industry_code_for(industry: str) -> str | None:
    """industry(예: "카페")에 대응하는 상권 API 업종코드(indsSclsCd)를 반환한다.

    매핑이 없으면 None — 호출하는 쪽이 텍스트 매칭으로 폴백한다(D-041).
    """
    return _INDUSTRY_CODE_MAP.get(industry)


def _haversine_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """두 좌표 사이의 거리를 미터 단위로 계산한다."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlambda / 2) ** 2
    return 2 * _EARTH_RADIUS_M * math.asin(math.sqrt(a))


def _matches_industry(store: dict, industry: str) -> bool:
    """업종 대/중/소분류명 중 하나라도 industry 문자열을 포함하면 동일 업종으로 본다.

    industry_code_for()로 업종코드를 찾을 수 없을 때만 쓰는 폴백이다(D-041) —
    텍스트 포함 매칭이라 "스터디룸/멀티방 카페"(R10202)처럼 이름에 업종명이
    우연히 들어간 다른 업종도 함께 잡히는 오탐 위험이 있다.
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
    stores: list[dict],
    total_count: int,
    industry: str | None,
    lat: float,
    lng: float,
    *,
    matched_stores: list[dict] | None = None,
    matched_total_count: int | None = None,
) -> dict:
    """반경내 상가업소 목록에서 계약 형식(docs/repo_contract.md)을 계산한다.

    matched_stores/matched_total_count가 주어지면(D-041/D-042: 업종코드 필터
    호출 결과) same_industry_count/nearest_distance_m을 그 값으로 계산한다 —
    stores(원본, 반경 내 최대 1000곳까지만 담김)를 텍스트로 다시 찾지 않는다.
    주어지지 않으면(코드 매핑이 없는 industry) 기존처럼 stores를 텍스트로
    매칭해 폴백한다(D-041).

    TODO: industry_breakdown은 여전히 stores(원본, 최대 1000곳)까지만 집계된다
    — D-041/D-042는 same_industry_count/nearest_distance_m 정확도만 다룬다.
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

    if matched_stores is not None and matched_total_count is not None:
        matches = [store for store in matched_stores if isinstance(store, dict)]
        same_industry_count = matched_total_count
    else:
        matches = [store for store in stores if _matches_industry(store, industry)]
        same_industry_count = len(matches)

    if not matches:
        return {
            "total_count": total_count,
            "same_industry_count": same_industry_count,
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
        "same_industry_count": same_industry_count,
        "nearest_distance_m": nearest,
        "industry_breakdown": industry_breakdown,
    }


def _request_stores(params: dict) -> tuple[list[dict], int] | None:
    """상권정보 OpenAPI(반경내 상가업소 조회)를 호출해 매장 목록·전체 매장 수를 반환한다.

    fetch_raw()(원본 조회)와 fetch_by_code()(업종코드 필터 조회, D-042)가 요청
    파라미터만 다르게 해서 공유하는 요청·파싱 로직이다. 실패 시 None.
    """
    try:
        response = httpx.get(_BASE_URL, params=params, timeout=10.0)
        response.raise_for_status()
        payload = response.json()
    except (httpx.HTTPError, ValueError):
        # ValueError: HTTP 200이어도 인증 실패 등으로 JSON이 아닌 본문(XML/텍스트)이 올 수 있음
        return None

    if not isinstance(payload, dict):
        # 유효한 JSON이어도 최상위가 dict가 아니면(예: 배열) 정상 응답으로 취급하지 않는다
        return None

    header = payload.get("header")
    if not isinstance(header, dict) or header.get("resultCode") != "00":
        # API가 HTTP 200으로 오류를 반환하는 경우(예: 인증키 오류) — 정상 데이터로 오인하지 않는다
        return None

    # JSON 응답은 XML 문서의 <response> 래퍼 없이 {"header":..., "body":...}로 온다(실측 확인).
    body = payload.get("body", {})
    if not isinstance(body, dict):
        return None

    items = body.get("items") or []
    item = items.get("item", []) if isinstance(items, dict) else items
    stores = [item] if isinstance(item, dict) else item
    if not isinstance(stores, list):
        # item이 리스트도 dict도 아닌 예상 밖 형태(숫자·문자열 등)면 정상 응답으로 취급하지 않는다
        return None

    try:
        total_count = int(body.get("totalCount", len(stores)))
    except (TypeError, ValueError):
        # totalCount가 숫자로 변환할 수 없는 값(문자열 등)이면 정상 응답으로 취급하지 않는다
        return None

    return stores, total_count


def _base_params(lat: float, lng: float, radius: int, api_key: str) -> dict:
    return {
        "serviceKey": api_key,
        "radius": radius,
        "cx": lng,
        "cy": lat,
        "numOfRows": 1000,
        "pageNo": 1,
        "type": "json",
    }


def fetch_raw(lat: float, lng: float, radius: int = 500) -> tuple[list[dict], int] | None:
    """상권정보 OpenAPI(반경내 상가업소 조회)를 호출해 원본 매장 목록·전체 매장 수를 반환한다.

    업종 필터 없이 원본만 반환한다 — market_repo가 이 결과를 업종과 무관하게 캐싱하고,
    aggregate()는 조회할 때마다 별도로 호출하기 위함(같은 좌표라도 industry가 다르면
    캐시를 재사용해야 하므로). 실패 시 None.

    MARKET_API_KEY는 디코딩 키를 쓴다 — httpx의 params=가 자동으로 URL 인코딩하므로,
    인코딩 키를 넣으면 이중 인코딩되어 인증에 실패한다.
    """
    api_key = os.getenv("MARKET_API_KEY")
    if not api_key:
        return None

    return _request_stores(_base_params(lat, lng, radius, api_key))


def fetch_by_code(lat: float, lng: float, radius: int, code: str) -> tuple[list[dict], int] | None:
    """indsSclsCd(업종코드)로 필터링된 매장 목록·전체 매장 수를 반환한다(D-042 ②호출).

    D-041에 따라 텍스트 매칭보다 정확한 동일업종 판정에 쓴다 — API 자체가
    서버 사이드로 필터링해주므로, 반경 내 전체 매장이 numOfRows(1000)를
    넘어도(예: 강남역 500m 6,691곳) 특정 소분류만 걸러진 totalCount는 정확하다.
    """
    api_key = os.getenv("MARKET_API_KEY")
    if not api_key:
        return None

    params = _base_params(lat, lng, radius, api_key)
    params["indsSclsCd"] = code
    return _request_stores(params)


def fetch(lat: float, lng: float, radius: int = 500, industry: str | None = None) -> dict | None:
    """상권정보 OpenAPI를 호출해 계약 형식(docs/repo_contract.md)으로 변환한다. 실패 시 None.

    industry에 대응하는 업종코드가 있으면(industry_code_for(), D-043) 업종코드
    필터 호출을 한 번 더 해서 same_industry_count/nearest_distance_m을 정확하게
    계산한다(D-041/D-042). 코드가 없거나 필터 호출 자체가 실패하면 원본 목록을
    텍스트로 매칭하는 방식으로 폴백한다(D-041) — 어느 쪽이든 결과 자체는 낸다.
    """
    fetched = fetch_raw(lat, lng, radius)
    if fetched is None:
        return None
    stores, total_count = fetched

    if industry is None:
        return aggregate(stores, total_count, industry, lat, lng)

    code = industry_code_for(industry)
    if code is not None:
        filtered = fetch_by_code(lat, lng, radius, code)
        if filtered is not None:
            matched_stores, matched_total_count = filtered
            return aggregate(
                stores,
                total_count,
                industry,
                lat,
                lng,
                matched_stores=matched_stores,
                matched_total_count=matched_total_count,
            )

    return aggregate(stores, total_count, industry, lat, lng)
