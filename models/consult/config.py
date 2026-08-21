# models/consult/config.py — 컨설턴트 챗봇 전용 설정값 (LLM 공통값은 models/shared/config.py가 단일 소스)
CACHE_TTL_MARKET_DAYS = 7  # 상권 캐시 TTL(SDP §2.7) — cache/market_repo.py에서 사용
CACHE_TTL_TREND_DAYS = 7  # 트렌드 캐시 TTL(SDP §2.7) — cache/trend_repo.py에서 사용

# SDP에 개수 제한 명시 없음 — 과도하게 긴 연관 검색어 목록을 막기 위한 자체 상한
# (search_ad_api.py에서 사용, D-235로 조정 지점을 여기 하나로 모음)
MAX_RELATED_KEYWORDS = 5

# backend.schemas.ConsultantStrategy.actions의 Field(min_length=1, max_length=3)과
# 반드시 같아야 한다 — 모델 프로덕션 코드는 backend를 import할 수 없어(§7.4) 값을
# 복제하지만, 계약 동기화 테스트(tests/test_strategy_contract.py)가 어긋남을 잡는다.
MIN_ACTIONS = 1
MAX_ACTIONS = 3
