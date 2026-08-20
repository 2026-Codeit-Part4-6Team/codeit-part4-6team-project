# models/consult/clients/search_ad_api.py — 네이버 검색광고(Search Ad) API 클라이언트(연관 검색어 조회)
#
# SDP 외 자체 확장: get_trend()의 related 필드는 SDP mock에 값 형태만 나와 있을 뿐
# 어떤 API로 채우라는 지시가 없다. 검색광고 API로 채우기로 자체 판단해 추가했고
# PM에게 사전 공유함(docs/decisions.md D-185 참고).
import base64
import hashlib
import hmac
import os
import time

import httpx

_BASE_URL = "https://api.searchad.naver.com"
_URI = "/keywordstool"
_MAX_RELATED_KEYWORDS = 5  # SDP에 개수 제한 명시 없음 — 과도하게 긴 리스트를 막기 위한 자체 상한


def _sign(secret_key: str, timestamp: str, method: str, uri: str) -> str:
    """네이버 검색광고 API 서명(HMAC-SHA256, base64)을 생성한다.

    데이터랩(API 키+시크릿 헤더)이나 API HUB(NCP 키 ID+키 헤더)와 달리, 검색광고
    API는 요청마다 타임스탬프+메서드+URI를 시크릿 키로 서명해야 한다.
    """
    message = f"{timestamp}.{method}.{uri}"
    digest = hmac.new(secret_key.encode("utf-8"), message.encode("utf-8"), hashlib.sha256).digest()
    return base64.b64encode(digest).decode("utf-8")


def fetch_related_keywords(keyword: str) -> list[str] | None:
    """연관 검색어를 조회한다. 실패(자격증명 없음·HTTP 오류·JSON 아님) 시 None을 반환한다.

    입력 키워드 자체는 결과에서 제외하고, 중복을 제거하며, 최대
    _MAX_RELATED_KEYWORDS개로 제한한다. API는 성공했지만 연관 검색어가 없으면
    빈 리스트를 반환한다(None과 구분 — "실패"와 "결과 없음"은 다르다).

    요청·비교에 쓰는 키워드는 공백을 전부 제거한다 — 이 API는 공백이 포함된
    키워드(예: "아이스 아메리카노")를 Invalid Parameter로 거부하는 사례가 있고,
    응답의 relKeyword도 공백 없이 올 수 있어 그대로 비교하면 입력 키워드 자체가
    연관어 목록에 남거나 중복 제거가 실패할 수 있다.
    """
    api_key = os.getenv("NAVER_AD_API_KEY")
    secret_key = os.getenv("NAVER_AD_SECRET_KEY")
    customer_id = os.getenv("NAVER_AD_CUSTOMER_ID")
    if not api_key or not secret_key or not customer_id:
        return None

    request_keyword = keyword.replace(" ", "")

    timestamp = str(int(time.time() * 1000))
    headers = {
        "X-Timestamp": timestamp,
        "X-API-KEY": api_key,
        "X-Customer": customer_id,
        "X-Signature": _sign(secret_key, timestamp, "GET", _URI),
    }
    params = {"hintKeywords": request_keyword, "showDetail": "1"}

    try:
        response = httpx.get(f"{_BASE_URL}{_URI}", params=params, headers=headers, timeout=10.0)
        response.raise_for_status()
        payload = response.json()
    except (httpx.HTTPError, ValueError):
        # ValueError: HTTP 200이어도 인증 실패 등으로 JSON이 아닌 본문이 올 수 있음
        return None

    if not isinstance(payload, dict):
        # 유효한 JSON이어도 최상위가 dict가 아니면(예: 배열) 정상 응답으로 취급하지 않는다
        return None

    keyword_list = payload.get("keywordList")
    if not isinstance(keyword_list, list):
        return None

    related: list[str] = []
    for item in keyword_list:
        if not isinstance(item, dict):
            continue
        rel_keyword = item.get("relKeyword")
        if not isinstance(rel_keyword, str) or not rel_keyword.strip():
            continue
        normalized = rel_keyword.strip().replace(" ", "")
        if not normalized or normalized == request_keyword or normalized in related:
            continue
        related.append(normalized)
        if len(related) >= _MAX_RELATED_KEYWORDS:
            break

    return related
