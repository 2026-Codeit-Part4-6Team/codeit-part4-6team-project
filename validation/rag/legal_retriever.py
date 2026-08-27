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
  "관련 법률 조문 3개"를 뽑는 데는 충분하다.
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


def _vector_scores(query: str) -> dict[str, float] | None:
    """법률 조문별 코사인 유사도(0~1). 인덱스나 키가 없으면 None."""
    if _load_vectors() is None:
        return None
    try:
        import numpy as np
        from openai import OpenAI

        resp = OpenAI(timeout=C.EMBED_TIMEOUT_SECONDS).embeddings.create(
            model=C.EMBED_MODEL, input=[query]
        )
        q = np.asarray(resp.data[0].embedding, dtype="float32")
        q /= (np.linalg.norm(q) or 1.0)
        raw = _vectors @ q                      # 정규화된 벡터라 내적 = 코사인
        return {cid: float((v + 1.0) / 2.0)     # -1~1 → 0~1 로 옮긴다
                for cid, v in zip(_vector_ids, raw, strict=False)}
    except Exception as e:  # noqa: BLE001
        logger.warning("벡터 검색 실패 → 어휘 검색만 사용: %s", type(e).__name__)
        return None



# ═════════════════════════════════════════════════════════════════════════════
# 로컬 모드
# ═════════════════════════════════════════════════════════════════════════════
def _bigrams(s: str) -> set[str]:
    s = "".join(s.split())
    return {s[i:i + 2] for i in range(len(s) - 1)} or {s}


def _lexical_scores(query: str) -> dict[str, float]:
    """법률 조문별 어휘 일치 점수(0~1). bigram Jaccard + 트리거 직접 매칭."""
    qb = _bigrams(query)
    out: dict[str, float] = {}
    for c in chunks():
        jacc = len(qb & _bigrams(c.get("embed_text", ""))) / (
            len(qb | _bigrams(c.get("embed_text", ""))) or 1
        )
        # 트리거 문자열이 질의에 그대로 들어 있으면 강한 신호다 —
        # legal_kb 의 위반 예시가 사용자 카피와 거의 같은 표현이기 때문이다.
        hit = min(sum(1 for t in c.get("triggers", []) if t and t in query) * 0.25, 1.0)
        out[c["id"]] = min(jacc + hit, 1.0)
    return out


def _hybrid_search(query: str, k: int, prefer_ids: list[str] | None) -> list[dict]:
    """벡터 유사도 · 어휘 일치 · 1단 트리거 힌트를 결합해 상위 k개를 고른다.

    ★ 왜 벡터만 쓰면 안 되나 (실측 근거)
      골든 24문항에서 벡터 단독은 recall 0.833 · Hit@1 0.625 였는데,
      어휘 검색은 recall 1.000 · Hit@1 0.958 이었다.
      legal_kb 의 '위반 예시' 가 사용자 카피와 거의 같은 표현이라
      이 도메인에서는 어휘 신호가 임베딩 유사도보다 강하다.
      게다가 36개 법률 조문이 전부 '광고 규제' 라 임베딩 공간에서 서로 가깝다.

    ★ 그렇다고 벡터를 버리지 않는 이유
      표현이 다른 변형(예: "저희가 제일입니다")은 어휘로 못 잡는다.
      §6.2.1 이 RAG 로 간 이유가 그것이므로 둘을 합친다.

    ★ prefer_ids 를 반드시 받는다
      1단이 이미 "REG-001 에 걸렸다" 를 알고 있다. 벡터 경로가 그 정보를
      버리는 것이 성능 저하의 직접 원인이었다.
    """
    vec = _vector_scores(query) if C.RAG_ENABLED else None
    lex = _lexical_scores(query)
    prefer = set(prefer_ids or [])
    mode_label = "hybrid" if vec else "local"

    scored: list[tuple[float, dict]] = []
    for c in chunks():
        score = C.HYBRID_W_LEXICAL * lex.get(c["id"], 0.0)
        if vec:
            score += C.HYBRID_W_VECTOR * vec.get(c["id"], 0.0)
        if c["id"] in prefer:
            score += C.HYBRID_W_PREFER
        scored.append((score, c))

    scored.sort(key=lambda x: -x[0])
    return [{**c, "score": round(sc, 4), "mode": mode_label} for sc, c in scored[:k]]


def _local_search(query: str, k: int, prefer_ids: list[str] | None = None) -> list[dict]:
    """벡터 없이 어휘만으로 검색한다(하위 호환 — 기존 호출부용)."""
    lex = _lexical_scores(query)
    prefer = set(prefer_ids or [])
    scored = [(lex.get(c["id"], 0.0) + (0.5 if c["id"] in prefer else 0.0), c)
              for c in chunks()]
    scored.sort(key=lambda x: -x[0])
    return [{**c, "score": round(sc, 4), "mode": "local"} for sc, c in scored[:k]]

# ═════════════════════════════════════════════════════════════════════════════
# 공개 API
# ═════════════════════════════════════════════════════════════════════════════
def search(query: str, k: int | None = None, prefer_ids: list[str] | None = None) -> list[dict]:
    """관련 법률 조문 청크를 k개 반환한다. 어떤 경우에도 예외를 던지지 않는다."""
    if k is None:
        # 1단이 지목한 법률 조문 수를 그대로 쓴다 — 없으면 기본값
        k = (min(max(len(prefer_ids or []), 1), C.MAX_TOP_K)
             if C.DYNAMIC_TOP_K and prefer_ids else C.RETRIEVE_TOP_K)
    if not chunks():
        return []
    # ★ 벡터가 성공해도 어휘 신호를 버리지 않는다 — 둘을 합쳐 한 번에 순위를 낸다.
    #   예전에는 벡터가 성공하면 로컬을 아예 안 타서 1단 트리거 힌트가 버려졌다.
    return _hybrid_search(query, k, prefer_ids)


def mode() -> str:
    """현재 검색 모드 — 로그·발표 자료용."""
    _load_vectors()
    if C.RAG_ENABLED and _vector_state == "ready" and C.has_openai_key():
        return "vector"
    return "local"
