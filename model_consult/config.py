# model_consult/config.py — 모델명·온도·재시도 등 컨설턴트 챗봇 공통 상수
OPENAI_MODEL = "gpt-4o-mini"  # 저비용 모델 기본값 — 여기 한 줄만 바꾸면 모델 교체 가능
LLM_TEMPERATURE = 0.3
LLM_MAX_RETRIES = 3  # 최초 호출 이후 재시도 횟수(SDP §6.5) — 총 시도 횟수는 4회
LLM_BACKOFF_SECONDS = [2, 4, 8]  # 재시도 1·2·3회차 대기 시간(초)
