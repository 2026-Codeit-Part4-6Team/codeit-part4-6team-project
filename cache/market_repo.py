# cache/market_repo.py — 상권 조회 Cache-Aside 구현(§2.7) · 두 챗봇 공용
import json
import logging
from datetime import UTC, datetime

from sqlalchemy.exc import SQLAlchemyError

from cache.db import SessionLocal
from cache.models import MarketCache
from cache.ttl import expired
from models.consult.clients.market_api import aggregate, fetch_by_code, fetch_raw, industry_code_for
from models.consult.config import CACHE_TTL_MARKET_DAYS

logger = logging.getLogger(__name__)


def get_market(
    lat: float, lng: float, radius: int = 500, industry: str | None = None
) -> dict | None:
    """상권 조회 — Cache-Aside(캐시 우선, 캐시 미스 시 API 실시간 호출 후 적재). 실패 시 None.

    원본(업종 무관, matched_stores 없이 캐싱)은 좌표별로 캐시를 공유해, 같은 좌표를
    다른 업종으로 조회해도 원본 재조회 없이 재사용한다. industry에 업종코드
    매핑이 있으면(industry_code_for(), D-043) 그 코드로 필터링된 결과도 (좌표,
    업종코드) 단위로 별도 캐싱한다(D-041/D-042) — 원본과 업종별 필터 결과는
    독립적으로 만료·재조회된다.
    좌표는 소수 3자리로 반올림해 캐시 키로 쓴다(약 100m 단위로 묶어 캐시를 공유).
    캐시 DB 조회·적재가 실패해도 API 실시간 호출로 폴백한다 — 캐시는 최적화일 뿐
    필수 의존성이 아니므로, DB 장애가 곧바로 컨설팅 응답 실패로 이어지면 안 된다.
    """
    round_lat, round_lng = round(lat, 3), round(lng, 3)

    cached = _read_cache(round_lat, round_lng, radius)
    if cached is not None:
        stores, total_count = cached["stores"], cached["total_count"]
    else:
        fetched = fetch_raw(lat, lng, radius)
        if fetched is None:
            return None
        stores, total_count = fetched
        _write_cache(round_lat, round_lng, radius, stores, total_count)

    if industry is None:
        return aggregate(stores, total_count, industry, lat, lng)

    code = industry_code_for(industry)
    if code is None:
        return aggregate(stores, total_count, industry, lat, lng)

    matched = _read_cache(round_lat, round_lng, radius, industry_code=code)
    if matched is not None:
        matched_stores, matched_total_count = matched["stores"], matched["total_count"]
    else:
        filtered = fetch_by_code(lat, lng, radius, code)
        if filtered is None:
            # 필터 호출 실패 — 원본을 텍스트로 매칭해 폴백한다(D-041)
            return aggregate(stores, total_count, industry, lat, lng)
        matched_stores, matched_total_count = filtered
        _write_cache(
            round_lat, round_lng, radius, matched_stores, matched_total_count, industry_code=code
        )

    return aggregate(
        stores,
        total_count,
        industry,
        lat,
        lng,
        matched_stores=matched_stores,
        matched_total_count=matched_total_count,
    )


def _read_cache(
    round_lat: float, round_lng: float, radius: int, industry_code: str | None = None
) -> dict | None:
    """신선한 캐시가 있으면 반환한다(industry_code가 None이면 원본, 있으면 그 업종코드로
    필터링된 결과).

    캐시가 없거나, DB 조회 자체가 실패하거나, 저장된 JSON이 기대한 형태가 아니면
    모두 캐시 미스로 간주해 None을 반환한다(호출하는 쪽이 API 실시간 호출로 폴백).
    캐시 히트/미스/DB 장애를 로그로 남긴다(적중률 측정·장애 추적용). API 키나
    응답 원문은 남기지 않는다.
    """
    key = f"lat={round_lat}, lng={round_lng}, radius={radius}, industry_code={industry_code}"
    try:
        with SessionLocal() as session:
            row = (
                session.query(MarketCache)
                .filter_by(lat=round_lat, lng=round_lng, radius=radius, industry_code=industry_code)
                # SQLite CURRENT_TIMESTAMP는 초 단위라 짧은 시간에 여러 번 적재되면
                # created_at이 같을 수 있다 — id로도 정렬해 항상 최신 행을 고른다.
                .order_by(MarketCache.created_at.desc(), MarketCache.id.desc())
                .first()
            )
            if row and not expired(row.created_at, days=CACHE_TTL_MARKET_DAYS):
                parsed = _parse_cached_payload(row.result_json)
                if parsed is not None:
                    logger.info("market cache hit (%s)", key)
                    return parsed
    except SQLAlchemyError:
        logger.warning("market cache read failed, falling back to live fetch (%s)", key)
        return None

    logger.info("market cache miss (%s)", key)
    return None


def _parse_cached_payload(result_json: str) -> dict | None:
    """result_json이 {"stores": list[dict], "total_count": int} 형태인지 검증한다.

    형태가 다르면(파싱 실패·손상·구버전 등) None을 반환해 캐시 미스로 처리한다 —
    예외를 종류별로 잡는 대신, 기대하는 형태를 직접 검증해 앞으로 어떤 손상 패턴이
    와도 같은 방어 로직 하나로 걸러진다.
    """
    try:
        cached = json.loads(result_json)
    except json.JSONDecodeError:
        return None

    if not isinstance(cached, dict):
        return None

    stores = cached.get("stores")
    total_count = cached.get("total_count")
    if not isinstance(stores, list) or not all(isinstance(s, dict) for s in stores):
        return None
    if not isinstance(total_count, int) or isinstance(total_count, bool):
        return None

    return {"stores": stores, "total_count": total_count}


def _write_cache(
    round_lat: float,
    round_lng: float,
    radius: int,
    stores: list[dict],
    total_count: int,
    industry_code: str | None = None,
) -> None:
    """캐시 적재는 최선 노력으로만 시도한다 — 실패해도 이미 확보한 실시간 결과 반환에는 영향 없다.

    같은 (lat, lng, radius, industry_code) 행이 이미 있으면 새로 추가하지 않고
    갱신한다(upsert, D-053) — market_cache에 UNIQUE 인덱스는 아직 없어(D7에 서비스
    담당이 DDL로 추가 예정) DB가 직접 중복 삽입을 막아주지 않는다. 그전까지는
    애플리케이션 레벨에서 미리 방어해야 캐시 미스가 반복될 때마다 오래된 행이
    계속 쌓이지 않는다.

    created_at은 항상 명시적으로 지금 시각으로 갱신한다 — result_json이 이전과
    같은 값이면 SQLAlchemy가 그 컬럼을 "변경 없음"으로 보고 UPDATE에서 빼버려서,
    모델의 onupdate=func.now()도 함께 발동하지 않는다(Codex 리뷰에서 실제 재현:
    동일 payload 재적재 시 created_at이 그대로 남아 다음 조회도 계속 만료로
    판정됨). created_at을 매번 직접 대입하면 값이 실제로 바뀌므로 이 문제가 없다.
    """
    payload = json.dumps({"stores": stores, "total_count": total_count})
    now = datetime.now(UTC).replace(tzinfo=None)
    try:
        with SessionLocal() as session:
            existing = (
                session.query(MarketCache)
                .filter_by(lat=round_lat, lng=round_lng, radius=radius, industry_code=industry_code)
                .order_by(MarketCache.created_at.desc(), MarketCache.id.desc())
                .first()
            )
            if existing is not None:
                existing.result_json = payload
                existing.created_at = now
            else:
                session.add(
                    MarketCache(
                        lat=round_lat,
                        lng=round_lng,
                        radius=radius,
                        industry_code=industry_code,
                        result_json=payload,
                    )
                )
            session.commit()
    except SQLAlchemyError:
        logger.warning(
            "market cache write failed, live fetch result still returned "
            "(lat=%s, lng=%s, radius=%s, industry_code=%s)",
            round_lat,
            round_lng,
            radius,
            industry_code,
        )
