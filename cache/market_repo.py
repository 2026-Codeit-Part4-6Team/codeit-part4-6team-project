# cache/market_repo.py — 상권 조회 Cache-Aside 구현(§2.7) · 두 챗봇 공용
import json
import logging

from sqlalchemy.exc import SQLAlchemyError

from cache.db import SessionLocal
from cache.models import MarketCache
from cache.ttl import expired
from models.consult.clients.market_api import aggregate, fetch_raw

logger = logging.getLogger(__name__)

_TTL_DAYS = 7


def get_market(
    lat: float, lng: float, radius: int = 500, industry: str | None = None
) -> dict | None:
    """상권 조회 — Cache-Aside(캐시 우선, 캐시 미스 시 API 실시간 호출 후 적재). 실패 시 None.

    캐시에는 industry와 무관한 원본(매장 목록·전체 매장 수)만 저장하고, industry별
    집계(aggregate)는 캐시 히트/미스와 상관없이 매번 새로 계산한다 — 그래야 같은 좌표를
    다른 업종으로 조회해도 캐시를 재사용하고, 매번 API를 다시 부르지 않는다.
    좌표는 소수 3자리로 반올림해 캐시 키로 쓴다(약 100m 단위로 묶어 캐시를 공유).
    캐시 DB 조회·적재가 실패해도 API 실시간 호출로 폴백한다 — 캐시는 최적화일 뿐
    필수 의존성이 아니므로, DB 장애가 곧바로 컨설팅 응답 실패로 이어지면 안 된다.
    """
    round_lat, round_lng = round(lat, 3), round(lng, 3)

    cached = _read_cache(round_lat, round_lng, radius)
    if cached is not None:
        return aggregate(cached["stores"], cached["total_count"], industry, lat, lng)

    fetched = fetch_raw(lat, lng, radius)
    if fetched is None:
        return None
    stores, total_count = fetched

    _write_cache(round_lat, round_lng, radius, stores, total_count)

    return aggregate(stores, total_count, industry, lat, lng)


def _read_cache(round_lat: float, round_lng: float, radius: int) -> dict | None:
    """신선한 캐시가 있으면 원본을 반환한다.

    캐시가 없거나, DB 조회 자체가 실패하거나, 저장된 JSON이 기대한 형태가 아니면
    모두 캐시 미스로 간주해 None을 반환한다(호출하는 쪽이 API 실시간 호출로 폴백).
    캐시 히트/미스/DB 장애를 로그로 남긴다(적중률 측정·장애 추적용). API 키나
    응답 원문은 남기지 않는다.
    """
    key = f"lat={round_lat}, lng={round_lng}, radius={radius}"
    try:
        with SessionLocal() as session:
            row = (
                session.query(MarketCache)
                .filter_by(lat=round_lat, lng=round_lng, radius=radius)
                .order_by(MarketCache.created_at.desc())
                .first()
            )
            if row and not expired(row.created_at, days=_TTL_DAYS):
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
    round_lat: float, round_lng: float, radius: int, stores: list[dict], total_count: int
) -> None:
    """캐시 적재는 최선 노력으로만 시도한다 — 실패해도 이미 확보한 실시간 결과 반환에는 영향 없다."""
    try:
        with SessionLocal() as session:
            session.add(
                MarketCache(
                    lat=round_lat,
                    lng=round_lng,
                    radius=radius,
                    result_json=json.dumps({"stores": stores, "total_count": total_count}),
                )
            )
            session.commit()
    except SQLAlchemyError:
        logger.warning(
            "market cache write failed, live fetch result still returned (lat=%s, lng=%s, radius=%s)",
            round_lat,
            round_lng,
            radius,
        )
