"""
validation/rag/legal_retriever.py
legal_kb 검색기.

★ 두 가지 모드를 갖는다
  1) 벡터 모드 — 사전 임베딩된 vectors.npy + text-embedding-3-small 쿼리 임베딩
  2) 로컬 모드 — 문자 bigram 유사도 + 트리거 정확 매칭 가중

  왜 로컬 모드가 필요한가:
    · CI 에는 OPENAI_API_KEY 가 없다. 그래도 스모크 테스트는 돌아야 한다.
    · $30 한도가 소진되거나 OpenAI 장애 시에도 서비스가 죽으면 안 된다.
    · 팀원이 키 없이 로컬에서 개발할 수 있어야 한다.
  로컬 모드는 정확도가 낮지만, 어차피 1단 트리거가 이미 후보를 좁혀준 뒤라
  "관련 조문 3개"를 뽑는 데는 충분하다.
"""

from __future__ import annotations

import json
import logging
from functools import lru_cache
from typing import Any

from .. import config as C

logger = logging.getLogger(__name__)


# ═════════════════════════════════════════════════════════════════════════════
# KB 로딩
# ═════════════════════════════════════════════════════════════════════════════
class LegalKBMissing(RuntimeError):
    """legal_kb 를 읽지 못했다 — 규제 검증을 무력화한 채 진행하지 않는다."""


_MISSING_MSG = (
    "legal_kb 를 읽지 못했다: {reason}\n"
    "  경로: {path}\n"
    "  → `uv run python scripts/build_legal_kb.py` 를 실행하고 "
    "shared_data/legal_kb.json 을 커밋했는지 확인하라.\n"
    "  이 파일이 없으면 1단 트리거 사전이 비어 check_regulation 이 "
    "모든 카피를 pass 시킨다(규제 검증 무력화).\n"
    "  KB 없이 다른 작업을 하려면 VALIDATION_REQUIRE_LEGAL_KB=0 을 설정한다."
)


@lru_cache(maxsize=1)
def load_kb() -> dict[str, Any]:
    """legal_kb.json 을 1회만 읽는다.

    ★ 읽지 못하면 조용히 빈 KB 로 넘어가지 않는다.
      빈 KB 는 "규제 위반이 없다" 가 아니라 "검사할 수단이 없다" 이고,
      둘을 같은 pass 로 처리하면 규제 검증이 통째로 무력화된 사실이 드러나지 않는다.
    """
    empty = {"chunks": [], "source_sha256": "", "count": 0}

    if not C.LEGAL_KB_JSON.exists():
        reason = "파일이 존재하지 않는다"
    else:
        try:
            data = json.loads(C.LEGAL_KB_JSON.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            reason = f"읽기·파싱 실패({type(exc).__name__})"
        else:
            count = len(data.get("chunks") or [])
            if count >= C.MIN_LEGAL_KB_CHUNKS:
                return data
            reason = f"청크가 {count}개뿐이다(최소 {C.MIN_LEGAL_KB_CHUNKS}개 필요)"

    message = _MISSING_MSG.format(reason=reason, path=C.LEGAL_KB_JSON)
    if C.REQUIRE_LEGAL_KB:
        raise LegalKBMissing(message)
    logger.error(message)
    return empty


@lru_cache(maxsize=1)
def chunks() -> list[dict]:
    return load_kb().get("chunks", [])


@lru_cache(maxsize=1)
def by_id() -> dict[str, dict]:
    return {c["id"]: c for c in chunks()}


# ═════════════════════════════════════════════════════════════════════════════
# 벡터 모드
# ═════════════════════════════════════════════════════════════════════════════
_vectors = None
_vector_ids: list[str] = []
_vector_state = "init"   # init | ready | unavailable


def _load_vectors():
    """사전 계산된 임베딩 행렬을 메모리에 올린다."""
    global _vectors, _vector_ids, _vector_state
    if _vector_state != "init":
        return
    try:
        import numpy as np

        if not (C.LEGAL_VECTORS_NPY.exists() and C.LEGAL_INDEX_META.exists()):
            _vector_state = "unavailable"
            return
        meta = json.loads(C.LEGAL_INDEX_META.read_text(encoding="utf-8"))
        if meta.get("source_sha256") != load_kb().get("source_sha256"):
            logger.warning(
                "legal_kb.md 가 인덱스보다 최신이다. "
                "`python scripts/build_legal_index.py` 재실행 필요 — 로컬 모드로 동작한다."
            )
            _vector_state = "unavailable"
            return
        _vectors = np.load(C.LEGAL_VECTORS_NPY)
        _vector_ids = meta["ids"]
        _vector_state = "ready"
    except Exception as e:  # noqa: BLE001
        logger.warning("벡터 인덱스 로딩 실패 → 로컬 모드: %s", e)
        _vector_state = "unavailable"


def embed_query(text: str) -> list[float] | None:
    """쿼리 1건 임베딩. 실패하면 None 을 돌려 로컬 모드로 넘긴다."""
    if not C.has_openai_key():
        return None
    try:
        from openai import OpenAI

        client = OpenAI(timeout=C.JUDGE_TIMEOUT_SEC)
        resp = client.embeddings.create(model=C.EMBED_MODEL, input=text[:2000])
        return resp.data[0].embedding
    except Exception as e:  # noqa: BLE001
        logger.warning("쿼리 임베딩 실패 → 로컬 모드: %s", e)
        return None


def _vector_search(query: str, k: int) -> list[dict] | None:
    _load_vectors()
    if _vector_state != "ready":
        return None
    vec = embed_query(query)
    if vec is None:
        return None
    import numpy as np

    q = np.asarray(vec, dtype="float32")
    q /= (np.linalg.norm(q) + 1e-9)
    scores = _vectors @ q                      # 저장 시 이미 정규화 → 내적 = 코사인
    order = np.argsort(-scores)[:k]
    idx = by_id()
    return [
        {**idx[_vector_ids[i]], "score": float(scores[i]), "mode": "vector"}
        for i in order
        if _vector_ids[i] in idx
    ]


# ═════════════════════════════════════════════════════════════════════════════
# 로컬 모드
# ═════════════════════════════════════════════════════════════════════════════
def _bigrams(s: str) -> set[str]:
    s = "".join(s.split())
    return {s[i:i + 2] for i in range(len(s) - 1)} or {s}


def _local_search(query: str, k: int, prefer_ids: list[str] | None = None) -> list[dict]:
    qb = _bigrams(query)
    prefer = set(prefer_ids or [])
    scored: list[tuple[float, dict]] = []
    for c in chunks():
        cb = _bigrams(c.get("embed_text", ""))
        jacc = len(qb & cb) / (len(qb | cb) or 1)
        # 1단 트리거로 이미 지목된 조항에 강한 가중치를 준다 —
        # 로컬 모드의 정확도는 여기서 대부분 확보된다.
        boost = 0.5 if c["id"] in prefer else 0.0
        hit = sum(1 for t in c.get("triggers", []) if t and t in query) * 0.05
        scored.append((jacc + boost + hit, c))
    scored.sort(key=lambda x: -x[0])
    return [{**c, "score": round(s, 4), "mode": "local"} for s, c in scored[:k]]


# ═════════════════════════════════════════════════════════════════════════════
# 공개 API
# ═════════════════════════════════════════════════════════════════════════════
def search(query: str, k: int | None = None, prefer_ids: list[str] | None = None) -> list[dict]:
    """관련 법률 조문 청크를 k개 반환한다. 어떤 경우에도 예외를 던지지 않는다."""
    k = k or C.RETRIEVE_TOP_K
    if not chunks():
        return []
    if C.RAG_ENABLED:
        hits = _vector_search(query, k)
        if hits:
            return hits
    return _local_search(query, k, prefer_ids)


def mode() -> str:
    """현재 검색 모드 — 로그·발표 자료용."""
    _load_vectors()
    if C.RAG_ENABLED and _vector_state == "ready" and C.has_openai_key():
        return "vector"
    return "local"
