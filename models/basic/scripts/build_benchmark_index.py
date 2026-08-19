"""업종 벤치마크 KB 데이터를 임베딩해 FAISS 인덱스로 만든다.

실행: uv run --locked --all-groups python -m models.basic.scripts.build_benchmark_index

개발용 목업 mock_benchmark_kb.json 사용(추후 shared_data/benchmark_kb.json으로 교체 예정)
"""

import json
from pathlib import Path

import faiss
import numpy as np

from models.basic.retrieval.embedder import embed

_KB_PATH = Path("shared_data/benchmark_kb.json")
_MOCK_KB_PATH = Path(__file__).parent.parent / "retrieval" / "mock_benchmark_kb.json"
_INDEX_DIR = Path(__file__).parent.parent / "retrieval" / "benchmark_index"


def _resolve_kb_path() -> Path:
    if _KB_PATH.exists():
        return _KB_PATH
    print(f"{_KB_PATH}가 아직 없어 mock 데이터({_MOCK_KB_PATH})로 인덱싱합니다.")
    return _MOCK_KB_PATH


def main() -> None:
    kb_path = _resolve_kb_path()
    entries = json.loads(kb_path.read_text(encoding="utf-8"))

    vectors = np.array([embed(e["copy"]) for e in entries], dtype="float32")
    faiss.normalize_L2(vectors)

    index = faiss.IndexFlatIP(vectors.shape[1])
    index.add(vectors)

    _INDEX_DIR.mkdir(parents=True, exist_ok=True)
    faiss.write_index(index, str(_INDEX_DIR / "index.faiss"))
    (_INDEX_DIR / "metadata.json").write_text(
        json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(f"{len(entries)}건 인덱싱 완료 → {_INDEX_DIR}")


if __name__ == "__main__":
    main()
