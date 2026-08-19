"""
models/shared/config.py 
— 두 챗봇 공통 LLM 설정 단일 소스 (관리: 전민재 PM, D-047)

LLM 호출에 필요한 '값'만 모은다. 호출 '동작'은 models/shared/llm.py 소유.

넣는 것: 두 챗봇이 100% 동일한 LLM 설정값
안 넣는 것:
  · 챗봇 전용 상수 → models/{basic,consult}/config.py
  · API 키 → .env 만 (코드에 절대 금지)
  · 크레딧 단가·무료 한도·서비스 타임아웃 → backend/config.py 가 단일 소스.
    여기에 복사하면 한쪽만 바뀌었을 때 조용히 어긋난다(D-054 재발 방지).
"""
import os

# ── 모델·provider ──────────────────────────────────────────────
# 기본값은 코드에 명시한다. env 는 override 전용 — 평가 산출물에 실제 사용값을
# 함께 기록해야 "무슨 모델로 낸 수치냐"에 답할 수 있다(D-079).
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL") or None  # 대체 provider 교체점(D-078)
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.3"))

# LLM Judge 전용 모델 — 생성 모델과 분리해야 A/B 비교 시 "자[尺]"가 고정된다(D-251).
# 기본값을 OPENAI_MODEL 과 같게 둬서, 명시적으로 설정하기 전까지는 비용이 변하지 않는다.
OPENAI_JUDGE_MODEL = os.getenv("OPENAI_JUDGE_MODEL") or OPENAI_MODEL

# ── 재시도(429) ────────────────────────────────────────────────
# retry.py 를 따로 두지 않는다 — 사용처가 llm.py 하나뿐이라 파일만 늘어난다.
LLM_MAX_RETRIES = 3                    # 최초 호출 포함 총 4회 시도
LLM_BACKOFF_SECONDS = (2, 4, 8)

# ── 시간 예산 ──────────────────────────────────────────────────
LLM_TIMEOUT_SECONDS = 20               # 단일 호출 상한
LLM_DEADLINE_SECONDS = 50              # 요청 전체 예산 (D-049)
# ※ 서비스 MODEL_REQUEST_TIMEOUT_SECONDS(60, backend/config.py 소유)보다
#   반드시 짧아야 한다. 그 값을 여기에 복사하지 않는다.