#!/usr/bin/env python
"""
scripts/build_legal_index.py
shared_data/legal_kb.json  →  shared_data/legal_index/{vectors.npy, meta.json}

실행:
    uv run python scripts/build_legal_index.py

★ 산출물은 Git 에 커밋한다 (D-276)
  · 36청크 × 1536차원 × float32 ≈ 220KB — 저장소 부담이 없다.
  · 임베딩 호출이 팀 전체에서 1회로 끝난다 ($30 한도 보호).
  · 누가 돌려도 같은 벡터를 쓰므로 골든 데이터셋 점수가 재현된다.
    각자 임베딩하면 같은 코드인데 점수가 달라져 원인 추적이 불가능해진다.

★ meta.json 에 legal_kb.md 의 해시를 넣는다.
  md 를 고치고 인덱스를 다시 안 만들면 retriever 가 감지해 로컬 모드로 내려간다.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from validation import config as C  # noqa: E402

BATCH = 64


def main() -> int:
    if not C.LEGAL_KB_JSON.exists():
        print("❌ legal_kb.json 이 없다. scripts/build_legal_kb.py 를 먼저 실행하라.", file=sys.stderr)
        return 1
    if not C.has_openai_key():
        print("❌ OPENAI_API_KEY 가 없다.", file=sys.stderr)
        return 1

    import numpy as np
    from openai import OpenAI

    kb = json.loads(C.LEGAL_KB_JSON.read_text(encoding="utf-8"))
    chunks = kb["chunks"]
    texts = [c["embed_text"] for c in chunks]

    client = OpenAI()
    vectors: list[list[float]] = []
    for i in range(0, len(texts), BATCH):
        resp = client.embeddings.create(model=C.EMBED_MODEL, input=texts[i:i + BATCH])
        vectors.extend(d.embedding for d in sorted(resp.data, key=lambda d: d.index))
        print(f"  임베딩 {min(i + BATCH, len(texts))}/{len(texts)}")

    mat = np.asarray(vectors, dtype="float32")
    mat /= (np.linalg.norm(mat, axis=1, keepdims=True) + 1e-9)   # 정규화 → 내적=코사인

    C.LEGAL_INDEX_DIR.mkdir(parents=True, exist_ok=True)
    np.save(C.LEGAL_VECTORS_NPY, mat)
    C.LEGAL_INDEX_META.write_text(
        json.dumps(
            {
                "ids": [c["id"] for c in chunks],
                "model": C.EMBED_MODEL,
                "dim": int(mat.shape[1]),
                "count": len(chunks),
                "source_sha256": kb["source_sha256"],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    # FAISS 는 선택 사항이다. 36청크에서는 numpy 내적이 더 빠르고 의존성도 없다.
    # 팀 벤치마크 RAG 와 스택을 맞춰야 하면 아래 주석을 푼다.
    # import faiss
    # index = faiss.IndexFlatIP(mat.shape[1]); index.add(mat)
    # faiss.write_index(index, str(C.LEGAL_INDEX_DIR / "legal.faiss"))

    print(f"✅ {len(chunks)}개 × {mat.shape[1]}차원 → {C.LEGAL_INDEX_DIR}")
    print(f"   예상 비용: 약 ${len(chunks) * 200 / 1_000_000 * 0.02:.5f} (1회성)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
