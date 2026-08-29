# models/consult/clients/trend_api.py — NAVER API HUB 검색어 트렌드 API 클라이언트
import math
import os
from datetime import UTC, datetime, timedelta

import httpx

from models.consult.clients import search_ad_api

_BASE_URL = "https://naverapihub.apigw.ntruss.com/search-trend/v1/search"
_LOOKBACK_DAYS = 30  # 최근 30일 추이로 상승/하락 판단
_DIRECTION_THRESHOLD_RATIO = 0.1  # 전반부 대비 후반부 평균이 10% 이상 변하면 상승/하락으로 판단


def _direction_from_series(data: list) -> str:
    """기간별 ratio(상대 검색량 지수) 시계열의 전반부·후반부 평균을 비교해
    상승/하락/유지를 판단한다. 절대적인 기준이 없어 밀도 등급(density_tier)과
    같은 성격의 근사치다 — TODO: 실제 데이터로 임계값(10%) 재조정 검토.
    """
    ratios = [
        point["ratio"]
        for point in data
        if isinstance(point, dict) and isinstance(point.get("ratio"), (int, float))
    ]
    if len(ratios) < 2:
        return "유지"

    mid = len(ratios) // 2
    first_avg = sum(ratios[:mid]) / mid
    second_avg = sum(ratios[mid:]) / (len(ratios) - mid)

    if first_avg == 0:
        return "상승" if second_avg > 0 else "유지"

    change_ratio = (second_avg - first_avg) / first_avg
    # 부동소수점 오차로 정확히 ±10%가 0.09999999999999994처럼 계산될 수 있어
    # math.isclose()로 경계값도 상승/하락으로 잡히게 한다.
    if change_ratio >= _DIRECTION_THRESHOLD_RATIO or math.isclose(
        change_ratio, _DIRECTION_THRESHOLD_RATIO
    ):
        return "상승"
    if change_ratio <= -_DIRECTION_THRESHOLD_RATIO or math.isclose(
        change_ratio, -_DIRECTION_THRESHOLD_RATIO
    ):
        return "하락"
    return "유지"


def fetch_raw(keyword: str) -> dict | None:
    """NAVER API HUB 검색어 트렌드 API를 호출해 원본 결과(results[0])를 반환한다. 실패 시 None."""
    client_id = os.getenv("NAVER_CLIENT_ID")
    client_secret = os.getenv("NAVER_CLIENT_SECRET")
    if not client_id or not client_secret:
        return None

    end = datetime.now(UTC).date()
    # 시작일·종료일 모두 포함되는 일간 구간이라 -1을 빼야 총 _LOOKBACK_DAYS일이 된다
    start = end - timedelta(days=_LOOKBACK_DAYS - 1)

    body = {
        "startDate": start.isoformat(),
        "endDate": end.isoformat(),
        "timeUnit": "date",
        "keywordGroups": [{"groupName": keyword, "keywords": [keyword]}],
    }
    headers = {
        "X-NCP-APIGW-API-KEY-ID": client_id,
        "X-NCP-APIGW-API-KEY": client_secret,
        "Content-Type": "application/json",
    }

    try:
        response = httpx.post(_BASE_URL, json=body, headers=headers, timeout=10.0)
        response.raise_for_status()
        payload = response.json()
    except (httpx.HTTPError, ValueError):
        # ValueError: HTTP 200이어도 인증 실패 등으로 JSON이 아닌 본문이 올 수 있음
        return None

    if not isinstance(payload, dict):
        # 유효한 JSON이어도 최상위가 dict가 아니면(예: 배열) 정상 응답으로 취급하지 않는다
        return None

    results = payload.get("results")
    if not isinstance(results, list) or not results:
        return None

    result = results[0]
    return result if isinstance(result, dict) else None


def fetch(keyword: str) -> dict | None:
    """NAVER API HUB 검색어 트렌드 API를 호출해 get_trend() 계약 형식으로 변환한다. 실패 시 None.

    related(연관 검색어)는 네이버 검색광고 API(search_ad_api)로 별도 조회한다 —
    인증 방식이 완전히 달라(서명 기반) 별도 클라이언트로 분리했다. 그 API가
    실패해도(자격증명 없음 등) 트렌드 조회 자체는 계속 진행한다(부분 성공 허용).
    다만 계약(docs/repo_contract.md) 상 related는 항상 list[str]이어야 하므로,
    search_ad_api 내부의 "실패"(None)와 "결과 없음"(빈 리스트) 구분은 여기서
    끝나고 빈 리스트로 정규화한다.
    """
    result = fetch_raw(keyword)
    if result is None:
        return None

    data = result.get("data")
    if not isinstance(data, list):
        return None

    related = search_ad_api.fetch_related_keywords(keyword)

    return {
        "keyword": keyword,
        "direction": _direction_from_series(data),
        "related": related if related is not None else [],
    }
