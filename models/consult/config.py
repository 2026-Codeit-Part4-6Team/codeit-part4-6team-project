# models/consult/config.py — 컨설턴트 챗봇 전용 설정값 (LLM 공통값은 models/shared/config.py가 단일 소스)
CACHE_TTL_MARKET_DAYS = 7  # 상권 캐시 TTL(SDP §2.7) — cache/market_repo.py에서 사용
CACHE_TTL_TREND_DAYS = 7  # 트렌드 캐시 TTL(SDP §2.7) — cache/trend_repo.py에서 사용
