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
JUDGE_CACHE_SIZE = int(os.getenv("VALIDATION_JUDGE_CACHE", "512"))

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
