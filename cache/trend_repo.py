# cache/trend_repo.py — 검색어 트렌드 조회 Cache-Aside(§2.7) · 두 챗봇 공용
import json
import logging
from datetime import UTC, datetime

from sqlalchemy.exc import SQLAlchemyError

from cache.db import SessionLocal
from cache.models import TrendCache
from cache.ttl import expired
from models.consult.clients import trend_api
from models.consult.config import CACHE_TTL_TREND_DAYS

logger = logging.getLogger(__name__)


def get_trend(keyword: str, industry: str | None = None) -> dict | None:
    """검색어 트렌드 조회 — Cache-Aside(캐시 우선, 캐시 미스 시 API 실시간 호출 후 적재). 실패 시 None.

    검색어는 캐시 키로 쓰기 전에 정규화(공백 제거)한다 — "아이스아메리카노"와
    "아이스 아메리카노"처럼 같은 의미의 검색어가 서로 다른 캐시 항목으로 쪼개지면
    적중률이 떨어지고 네이버 트렌드 API 월 5만 건 한도를 불필요하게 더 쓰게 된다.
    실제 API 호출에도 정규화된 값을 그대로 써서, 캐시에 저장된 값과 실제로 조회한
    값이 항상 일치하게 한다.

    industry는 계약(docs/repo_contract.md)상 시그니처에는 있지만 아직 결과에
    영향을 주지 않는다(TODO: 실제 쓰임이 정해지면 캐시 키·API 호출에 반영 검토).

    캐시 DB 조회·적재가 실패해도 API 실시간 호출로 폴백한다 — 캐시는 최적화일 뿐
    필수 의존성이 아니므로, DB 장애가 곧바로 컨설팅 응답 실패로 이어지면 안 된다.
    """
    normalized_keyword = _normalize_keyword(keyword)

    cached = _read_cache(normalized_keyword)
    if cached is not None:
        return cached

    fetched = trend_api.fetch(normalized_keyword)
    if fetched is None:
        return None

    _write_cache(normalized_keyword, fetched)

    return fetched


def _normalize_keyword(keyword: str) -> str:
    """캐시 키·API 요청에 일관되게 쓸 정규화된 검색어(공백 제거)."""
    return keyword.replace(" ", "")


def _read_cache(keyword: str) -> dict | None:
    """신선한 캐시가 있으면 결과를 반환한다.

    캐시가 없거나, DB 조회 자체가 실패하거나, 저장된 JSON이 기대한 형태가 아니면
    모두 캐시 미스로 간주해 None을 반환한다(호출하는 쪽이 API 실시간 호출로 폴백).
    """
    try:
        with SessionLocal() as session:
            row = (
                session.query(TrendCache)
                .filter_by(keyword=keyword)
                # SQLite CURRENT_TIMESTAMP는 초 단위라 짧은 시간에 여러 번 적재되면
                # created_at이 같을 수 있다 — id로도 정렬해 항상 최신 행을 고른다.
                .order_by(TrendCache.created_at.desc(), TrendCache.id.desc())
                .first()
            )
            if row and not expired(row.created_at, days=CACHE_TTL_TREND_DAYS):
                parsed = _parse_cached_payload(row.result_json)
                if parsed is not None:
                    logger.info("trend cache hit (keyword=%s)", keyword)
                    return parsed
    except SQLAlchemyError:
        logger.warning("trend cache read failed, falling back to live fetch (keyword=%s)", keyword)
        return None

    logger.info("trend cache miss (keyword=%s)", keyword)
    return None


def _parse_cached_payload(result_json: str) -> dict | None:
    """result_json이 get_trend() 계약 형식인지 검증한다.

    형태가 다르면(파싱 실패·손상·구버전 등) None을 반환해 캐시 미스로 처리한다.
    """
    try:
        cached = json.loads(result_json)
    except json.JSONDecodeError:
        return None

    if not isinstance(cached, dict):
        return None

    keyword = cached.get("keyword")
    direction = cached.get("direction")
    related = cached.get("related")
    weather = cached.get("weather")
    if not isinstance(keyword, str):
        return None
    if direction not in {"상승", "하락", "유지"}:
        return None
    if not isinstance(related, list) or not all(isinstance(item, str) for item in related):
        return None
    if not _is_valid_weather(weather):
        return None

    return {
        "keyword": keyword,
        "direction": direction,
        "related": related,
        "weather": weather,
    }


def _is_valid_weather(weather: object) -> bool:
    """weather는 None이거나 {"temp": float, "sky": str} 형태만 허용한다(계약서 기준).

    형식이 다르면(문자열·리스트·필드 누락·타입 불일치 등) 캐시 전체를 무효로
    처리한다 — 검증 없이 그대로 반환하면 이 필드를 쓰는 쪽(예: 기본 챗봇의
    weather["temp"] 접근)에서 예외가 날 수 있다.
    """
    if weather is None:
        return True
    if not isinstance(weather, dict):
        return False
    temp = weather.get("temp")
    sky = weather.get("sky")
    if isinstance(temp, bool) or not isinstance(temp, (int, float)):
        return False
    return isinstance(sky, str) and bool(sky.strip())


def _write_cache(keyword: str, result: dict) -> None:
    """캐시 적재는 최선 노력으로만 시도한다 — 실패해도 이미 확보한 실시간 결과 반환에는 영향 없다.

    같은 keyword 행이 이미 있으면 새로 추가하지 않고 갱신한다(upsert, D-053과 동일
    패턴) — trend_cache에 UNIQUE 인덱스가 없어 DB가 직접 중복 삽입을 막아주지
    않으므로, 애플리케이션 레벨에서 미리 방어해야 캐시 미스가 반복될 때마다 오래된
    행이 계속 쌓이지 않는다.

    created_at은 항상 명시적으로 지금 시각으로 갱신한다 — result_json이 이전과
    같은 값이면 SQLAlchemy가 그 컬럼을 "변경 없음"으로 보고 UPDATE에서 빼버려서,
    갱신이 안 되면 다음 조회도 계속 만료로 판정돼 매번 실시간 API를 다시 호출하게
    된다(market_repo에서 Codex 리뷰로 발견된 것과 같은 유형).
    """
    payload = json.dumps(result, ensure_ascii=False)
    now = datetime.now(UTC).replace(tzinfo=None)
    try:
        with SessionLocal() as session:
            existing = (
                session.query(TrendCache)
                .filter_by(keyword=keyword)
                .order_by(TrendCache.created_at.desc(), TrendCache.id.desc())
                .first()
            )
            if existing is not None:
                existing.result_json = payload
                existing.created_at = now
            else:
                session.add(TrendCache(keyword=keyword, result_json=payload))
            session.commit()
    except SQLAlchemyError:
        logger.warning("trend cache write failed, live fetch result still returned (keyword=%s)", keyword)
