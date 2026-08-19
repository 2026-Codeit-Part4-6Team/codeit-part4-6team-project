import json
from pathlib import Path

import faiss
import numpy as np

from .embedder import embed

_INDEX_DIR = Path(__file__).parent / "benchmark_index"

_index = None
_metadata: list[dict] | None = None


def _load():
    """벤치마크 벡터 인덱스를 로드한다."""
    global _index, _metadata
    if _index is None:
        index_path = _INDEX_DIR / "index.faiss"
        metadata_path = _INDEX_DIR / "metadata.json"
        if not index_path.exists():
            return None, None
        _index = faiss.read_index(str(index_path))
        _metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    return _index, _metadata


def search_benchmark(query: str, k: int = 3) -> list[dict]:
    """쿼리와 유사한 벤치마크 사례 상위 k개를 검색해 반환한다."""
    index, metadata = _load()
    if index is None:
        return []

    query_vector = np.array([embed(query)], dtype="float32")
    faiss.normalize_L2(query_vector)

    _, indices = index.search(query_vector, min(k, len(metadata)))
    return [metadata[i] for i in indices[0] if i != -1]
