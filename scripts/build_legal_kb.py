#!/usr/bin/env python
"""
scripts/build_legal_kb.py
shared_data/legal_kb.md  →  shared_data/legal_kb.json

실행:
    uv run python scripts/build_legal_kb.py
    uv run python scripts/build_legal_kb.py --check   # CI용: 재생성 없이 동기화 여부만 확인

★ 임베딩 텍스트에 '위반 예시'를 반드시 넣는다 (계약서 §6.3.3)
  사용자 카피는 "우리 가게가 최고예요" 같은 구어체인데 법률 조문은 문어체다.
  조문만 임베딩하면 벡터 거리가 멀어 검색이 안 된다.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from validation import config as C

HEADER_RE = re.compile(r"^##\s+(REG-\d+)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*(warn|block)\s*$")
SECTION_RE = re.compile(r"^\*\*(.+?)\*\*\s*$")

SECTION_KEY = {
    "금지 내용": "text",
    "위반 예시": "bad_examples",
    "허용 예시": "good_examples",
    "대안 가이드": "action_guide",
    "트리거": "triggers",
    "예외 표현": "exceptions",
}
LIST_FIELDS = {"bad_examples", "good_examples", "triggers", "exceptions"}
PLACEHOLDER = {"(해당 없음)", "(없음)", "(해당 없음 — 대체 문구를 제안하지 않는다)"}


def parse(md_text: str) -> list[dict]:
    chunks: list[dict] = []
    cur: dict | None = None
    section: str | None = None
    buf: list[str] = []

    def flush() -> None:
        nonlocal buf, section
        if cur is not None and section:
            if section in LIST_FIELDS:
                cur[section] = [
                    ln.lstrip("- ").strip()
                    for ln in buf
                    if ln.strip().startswith("-")
                    and ln.lstrip("- ").strip() not in PLACEHOLDER
                ]
            else:
                cur[section] = "\n".join(buf).strip()
        buf, section = [], None

    for line in md_text.splitlines():
        if line.startswith("<!--") or line.startswith("#") and not line.startswith("##"):
            continue
        m = HEADER_RE.match(line)
        if m:
            flush()
            if cur:
                chunks.append(cur)
            cur = {
                "id": m.group(1),
                "law": m.group(2),
                "category": m.group(3),
                "severity": m.group(4),
                "text": "",
                "bad_examples": [],
                "good_examples": [],
                "action_guide": "",
                "triggers": [],
                "exceptions": [],
            }
            continue
        if cur is None:
            continue
        s = SECTION_RE.match(line.strip())
        if s and s.group(1) in SECTION_KEY:
            flush()
            section = SECTION_KEY[s.group(1)]
            continue
        if line.strip() == "---":
            flush()
            continue
        if section:
            buf.append(line)

    flush()
    if cur:
        chunks.append(cur)
    return chunks


def build_embed_text(c: dict) -> str:
    """검색 품질을 좌우하는 부분. 조문 + 위반 예시를 함께 넣는다."""
    bad = " / ".join(c["bad_examples"])
    good = " / ".join(c["good_examples"])
    return (
        f"{c['category']} — {c['law']}\n"
        f"{c['text']}\n"
        f"위반 예시: {bad}\n"
        f"허용 예시: {good}"
    ).strip()


def validate(chunks: list[dict]) -> list[str]:
    errs: list[str] = []
    seen: set[str] = set()
    for c in chunks:
        cid = c["id"]
        if cid in seen:
            errs.append(f"{cid}: ID 중복")
        seen.add(cid)
        if not c["text"]:
            errs.append(f"{cid}: '금지 내용'이 비어 있음")
        if c["severity"] == "warn":
            if not c["good_examples"]:
                errs.append(f"{cid}: warn 인데 '허용 예시'가 없음 → 대안 제시율 지표가 깨진다")
            if not c["action_guide"]:
                errs.append(f"{cid}: warn 인데 '대안 가이드'가 없음")
        if not c["triggers"]:
            errs.append(f"{cid}: '트리거'가 없음 → 1단 스크리닝에서 절대 걸리지 않는다")
    return errs


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="재생성 없이 동기화 여부만 확인")
    args = ap.parse_args()

    md_text = C.LEGAL_KB_MD.read_text(encoding="utf-8")
    chunks = parse(md_text)

    errs = validate(chunks)
    if errs:
        print("❌ legal_kb.md 검증 실패:", file=sys.stderr)
        for e in errs:
            print("   -", e, file=sys.stderr)
        return 1

    for c in chunks:
        c["embed_text"] = build_embed_text(c)

    payload = {
        "source_sha256": hashlib.sha256(md_text.encode("utf-8")).hexdigest(),
        "count": len(chunks),
        "chunks": chunks,
    }

    if args.check:
        if not C.LEGAL_KB_JSON.exists():
            print("❌ legal_kb.json 이 없다. build_legal_kb.py 를 실행하라.", file=sys.stderr)
            return 1
        old = json.loads(C.LEGAL_KB_JSON.read_text(encoding="utf-8"))
        if old.get("source_sha256") != payload["source_sha256"]:
            print("❌ legal_kb.md 가 바뀌었는데 json 이 갱신되지 않았다.", file=sys.stderr)
            return 1
        print(f"✅ 동기화 OK ({payload['count']}개 청크)")
        return 0

    C.LEGAL_KB_JSON.parent.mkdir(parents=True, exist_ok=True)
    C.LEGAL_KB_JSON.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    by_cat: dict[str, int] = {}
    for c in chunks:
        by_cat[c["category"]] = by_cat.get(c["category"], 0) + 1
    print(f"✅ {len(chunks)}개 청크 → {C.LEGAL_KB_JSON}")
    for k, v in sorted(by_cat.items(), key=lambda x: -x[1]):
        print(f"   {k:<10} {v}")
    print(f"   트리거 총 {sum(len(c['triggers']) for c in chunks)}개 / "
          f"예외 {sum(len(c['exceptions']) for c in chunks)}개")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
