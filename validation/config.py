"""
validation/config.py
검증 함수 4종 공통 설정.

★ 설계 원칙
  · 튜닝 가능한 숫자는 전부 여기 모은다. 코드 안에 매직넘버를 두지 않는다.
  · 환경변수로 덮어쓸 수 있게 해서, 골든 평가 때만 값을 바꿔 돌릴 수 있게 한다.
  · OPENAI_API_KEY 가 없어도 import 가 깨지지 않는다 (CI·오프라인 개발 대응).
"""

from __future__ import annotations

import os
from pathlib import Path


def _load_dotenv() -> None:
    """프로젝트 루트 .env 를 프로세스 환경에 올린다.

    ★ os.getenv 는 **셸 환경변수**만 본다. .env 파일에 써도 아무도 안 읽으면
      기본값이 그대로 쓰인다 — 실제로 VALIDATION_TOP_K=2 를 .env 에 넣었는데
      top_k 가 3 으로 돌아 측정이 무의미해졌다.
      이미 셸에 설정된 값은 덮어쓰지 않는다(CI·일회성 실행이 우선).
    """
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


_load_dotenv()

# ── 경로 ──────────────────────────────────────────────────────────────────────
# validation/config.py -> validation/ -> 프로젝트 루트
ROOT = Path(__file__).resolve().parent.parent

LEGAL_KB_MD = Path(os.getenv("LEGAL_KB_MD", ROOT / "shared_data" / "legal_kb.md"))
LEGAL_KB_JSON = Path(os.getenv("LEGAL_KB_JSON", ROOT / "shared_data" / "legal_kb.json"))
LEGAL_INDEX_DIR = Path(os.getenv("LEGAL_INDEX_DIR", ROOT / "shared_data" / "legal_index"))
LEGAL_VECTORS_NPY = LEGAL_INDEX_DIR / "vectors.npy"
LEGAL_INDEX_META = LEGAL_INDEX_DIR / "meta.json"

# ── 모델 ──────────────────────────────────────────────────────────────────────
# ⚠️ 모델 문자열은 프로젝트 가이드 "(2026.05 기준)" 표를 따랐다.
#    실제 발급받은 키에서 사용 가능한지 D-270 당일 1회 확인하고, 다르면 .env 로 덮어쓴다.
EMBED_MODEL = os.getenv("VALIDATION_EMBED_MODEL", "text-embedding-3-small")
JUDGE_MODEL = os.getenv("VALIDATION_JUDGE_MODEL", "gpt-5.4-mini")

EMBED_DIM = int(os.getenv("VALIDATION_EMBED_DIM", "1536"))

# ── 2단 RAG 판정 예산 방어 ────────────────────────────────────────────────────
JUDGE_TIMEOUT_SEC = float(os.getenv("VALIDATION_JUDGE_TIMEOUT", "8"))
JUDGE_MAX_TOKENS = int(os.getenv("VALIDATION_JUDGE_MAX_TOKENS", "400"))
JUDGE_TEMPERATURE = 0.0          # 재현성 — 골든 평가가 매번 달라지면 안 된다
RETRIEVE_TOP_K = int(os.getenv("VALIDATION_TOP_K", "3"))
# ★ 1단 트리거가 지목한 법률 조문 수만큼만 가져온다(D-검색개선).
#   1단은 이미 "어느 조항에 걸렸는지" 를 안다. 고정 k=3 은 정답이 1~2개인 문항에서
#   나머지를 채우느라 precision 을 깎았다 — 실측 0.389.
#   동적 k 는 recall 0.958 을 유지하면서 precision 0.958 로 올린다.
DYNAMIC_TOP_K = os.getenv("VALIDATION_DYNAMIC_TOP_K", "1") != "0"
MAX_TOP_K = int(os.getenv("VALIDATION_MAX_TOP_K", "3"))
JUDGE_CACHE_SIZE = int(os.getenv("VALIDATION_JUDGE_CACHE", "512"))

# ★ legal_kb 가 비어 있을 때 어떻게 할 것인가 (CI 사고 대응)
#   legal_kb.json 은 build_legal_kb.py 가 만드는 생성물이다. 이 파일이 없으면
#   1단 트리거 사전이 비어 check_regulation 이 **모든 카피를 조용히 pass** 시킨다 —
#   규제 검증이 통째로 무력화되는데 로그 경고 한 줄만 남는다(fail-open).
#   D-271 이 fail-open 을 배제했는데 KB 부재 경로만 예외로 남아 있었다.
#   기본값 1: KB 가 비면 즉시 RuntimeError 로 멈춘다.
#   개발 중 KB 없이 다른 작업을 하려면 0 으로 내린다.
REQUIRE_LEGAL_KB = os.getenv("VALIDATION_REQUIRE_LEGAL_KB", "1") != "0"

# KB 가 정상이라면 최소 이만큼은 있어야 한다(현재 36청크).
# 파싱이 일부만 성공한 경우도 잡는다.
MIN_LEGAL_KB_CHUNKS = int(os.getenv("VALIDATION_MIN_KB_CHUNKS", "30"))

# 2단 판정을 아예 끄는 스위치 (예산 소진 / 장애 / 오프라인 데모용)
# "0" 이면 1단 키워드 + KB 규칙 대안만으로 degrade 동작한다.
RAG_ENABLED = os.getenv("VALIDATION_RAG_ENABLED", "1") != "0"

# ── 입력 상한 ─────────────────────────────────────────────────────────────────
MAX_INPUT_CHARS = int(os.getenv("VALIDATION_MAX_INPUT_CHARS", "2000"))
MIN_INPUT_CHARS = int(os.getenv("VALIDATION_MIN_INPUT_CHARS", "2"))

# ── self_check 임계값 ─────────────────────────────────────────────────────────
MIN_COPY_LEN = int(os.getenv("SELF_CHECK_MIN_COPY_LEN", "6"))
EXPECTED_PROPOSALS = int(os.getenv("SELF_CHECK_EXPECTED_PROPOSALS", "3"))  # D-018 3안 고정
MIN_SUMMARY_LEN = int(os.getenv("SELF_CHECK_MIN_SUMMARY_LEN", "30"))
MIN_ACTIONS = int(os.getenv("SELF_CHECK_MIN_ACTIONS", "2"))
MIN_REASONS = int(os.getenv("SELF_CHECK_MIN_REASONS", "1"))


def has_openai_key() -> bool:
    """키가 없으면 2단 RAG 를 건너뛰고 degrade 경로를 탄다."""
    return bool(os.getenv("OPENAI_API_KEY"))

# ── 하이브리드 검색 가중치 (실측으로 조정한다) ────────────────────────────────
# 이 도메인에서는 어휘 신호가 임베딩보다 강하다 — legal_kb 의 위반 예시가
# 사용자 카피와 거의 같은 표현이기 때문이다(골든 24문항 실측:
# 어휘 Hit@1 0.958 vs 벡터 0.625). 그래서 어휘에 더 큰 가중치를 준다.
HYBRID_W_LEXICAL = float(os.getenv("VALIDATION_HYBRID_W_LEXICAL", "0.5"))
HYBRID_W_VECTOR = float(os.getenv("VALIDATION_HYBRID_W_VECTOR", "0.3"))
HYBRID_W_PREFER = float(os.getenv("VALIDATION_HYBRID_W_PREFER", "0.4"))
