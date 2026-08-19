"""골든 데이터셋 area=basic 문항으로 이미지 생성 결과를 평가한다.

B- 문항 중 지정된 개수(기본 20개)를 골라 카피 생성 → 이미지 생성 → CLIP
Score(정합성)·Aesthetic Score(미적 품질)를 산출한다. 멀티모달 LLM-Judge는
비용이 더 커서 별도 단계로 남겨둔다.

Aesthetic Score는 LAION Aesthetic Predictor(CLIP ViT-L/14 임베딩 기반 소형
MLP)를 이 파일 안에서 직접 로드한다 — CLIP Score용 인스턴스(ViT-B/32,
image_review.py)와는 별도 인스턴스다(체크포인트가 요구하는 임베딩 차원이
다름). 체크포인트는 최초 호출 시 이 파일과 같은 디렉토리에 자동
다운로드·캐시된다.

실행: uv run python -m models.basic.eval.eval_image \
    --dataset shared_data/golden_dataset.json --limit 20

models/shared/eval_fixtures.py 파일 도착 후 실행 가능하다.

참고: https://github.com/christophschuhmann/improved-aesthetic-predictor
"""

import argparse
import base64
import io
import json
import sys
import time
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

import torch
from PIL import Image
from torch import nn
from transformers import CLIPModel, CLIPProcessor

from models.basic.clients.image_client import IMAGE_MODEL, generate_image
from models.basic.nodes.copy_gen import copy_gen_node
from models.basic.nodes.image_gen import _build_image_prompt, _english_caption
from models.basic.nodes.image_review import _clip_score
from models.shared.config import OPENAI_MODEL
from models.shared.eval_fixtures import build_model_request

DATASET_VERSION = "v1.2"
_OUTPUT_DIR = Path(__file__).parent / "image_samples"

# Aesthetic Score (LAION Aesthetic Predictor)

_AESTHETIC_CHECKPOINT_URL = (
    "https://raw.githubusercontent.com/christophschuhmann/"
    "improved-aesthetic-predictor/main/sac%2Blogos%2Bava1-l14-linearMSE.pth"
)
_AESTHETIC_CHECKPOINT_PATH = Path(__file__).parent / "aesthetic_predictor.pth"

_aesthetic_clip_model = None
_aesthetic_clip_processor = None
_aesthetic_predictor = None


class _AestheticMLP(nn.Module):
    """LAION improved-aesthetic-predictor와 동일한 구조(CLIP L/14 768차원 입력)."""

    def __init__(self, input_size: int = 768):
        super().__init__()
        self.layers = nn.Sequential(
            nn.Linear(input_size, 1024),
            nn.Dropout(0.2),
            nn.Linear(1024, 128),
            nn.Dropout(0.2),
            nn.Linear(128, 64),
            nn.Dropout(0.1),
            nn.Linear(64, 16),
            nn.Linear(16, 1),
        )

    def forward(self, x):
        return self.layers(x)


def _load_aesthetic_clip():
    global _aesthetic_clip_model, _aesthetic_clip_processor
    if _aesthetic_clip_model is None:
        _aesthetic_clip_model = CLIPModel.from_pretrained(
            "openai/clip-vit-large-patch14"
        )
        _aesthetic_clip_processor = CLIPProcessor.from_pretrained(
            "openai/clip-vit-large-patch14"
        )
    return _aesthetic_clip_model, _aesthetic_clip_processor


def _load_aesthetic_predictor() -> _AestheticMLP:
    global _aesthetic_predictor
    if _aesthetic_predictor is None:
        if not _AESTHETIC_CHECKPOINT_PATH.exists():
            _AESTHETIC_CHECKPOINT_PATH.parent.mkdir(parents=True, exist_ok=True)
            urllib.request.urlretrieve(
                _AESTHETIC_CHECKPOINT_URL, _AESTHETIC_CHECKPOINT_PATH
            )
        _aesthetic_predictor = _AestheticMLP()
        _aesthetic_predictor.load_state_dict(
            torch.load(_AESTHETIC_CHECKPOINT_PATH, map_location="cpu")
        )
        _aesthetic_predictor.eval()
    return _aesthetic_predictor


def aesthetic_score(image: Image.Image) -> float:
    """이미지의 미적 품질 점수를 1~10 스케일로 반환한다(높을수록 좋음)."""
    model, processor = _load_aesthetic_clip()
    predictor = _load_aesthetic_predictor()

    inputs = processor(images=image, return_tensors="pt")
    with torch.no_grad():
        vision_outputs = model.vision_model(pixel_values=inputs["pixel_values"])
        image_embed = model.visual_projection(vision_outputs.pooler_output)
        image_embed = image_embed / image_embed.norm(dim=-1, keepdim=True)
        score = predictor(image_embed.float())

    return score.item()


# 골든 데이터셋 기반 평가


def _pick_copy(copy_candidates: list[dict]) -> str | None:
    for candidate in copy_candidates:
        if candidate.get("copy"):
            return candidate["copy"]
    return None


def _evaluate_item(item: dict) -> dict:
    request = build_model_request(item)
    store = request["store"]

    copy_result = copy_gen_node(
        {
            "question": request["question"],
            "platform": request["platform"],
            "store": store,
            "extra": request.get("extra") or {},
            "context": {},
        }
    )
    copy = _pick_copy(copy_result.get("copy_candidates", []))
    if not copy:
        return {"id": item["id"], "passed": False, "reason": "copy_generation_failed"}

    image_prompt = _build_image_prompt(store, copy)
    start = time.monotonic()
    image_b64 = generate_image(image_prompt)
    latency = time.monotonic() - start
    image = Image.open(io.BytesIO(base64.b64decode(image_b64)))

    caption = _english_caption(store.get("type", "store"), copy)
    clip = _clip_score(image, caption or image_prompt)
    aesthetic = aesthetic_score(image)

    image_path = _OUTPUT_DIR / f"{item['id']}.png"
    image.save(image_path)

    return {
        "id": item["id"],
        "passed": True,
        "copy": copy,
        "image_prompt": image_prompt,
        "caption_en": caption,
        "clip_score": clip,
        "aesthetic_score": aesthetic,
        "latency_s": round(latency, 2),
        "image_path": str(image_path),
    }


def run(dataset_path: Path, limit: int) -> dict:
    all_items = json.loads(dataset_path.read_text(encoding="utf-8"))
    items = [i for i in all_items if i["area"] == "basic"][:limit]

    if not items:
        print("basic 문항이 없습니다.", file=sys.stderr)
        sys.exit(1)

    _OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    results = []
    for item in items:
        print(f"처리 중: {item['id']}...")
        result = _evaluate_item(item)
        results.append(result)
        time.sleep(1)  # 직렬 실행 + 요청 간 sleep (§10.4·§10.5)

    processed = len(results)
    if processed != len(items):
        print(f"basic {len(items)}문항 중 {processed}건 처리 — 불일치", file=sys.stderr)
        sys.exit(1)
    print(f"basic {len(items)}문항 중 {processed}건 처리")

    passed = [r for r in results if r["passed"]]
    clip_scores = [r["clip_score"] for r in passed]
    aesthetic_scores = [r["aesthetic_score"] for r in passed]

    report = {
        "run_at": datetime.now(UTC).isoformat(),
        "area": "basic_image",
        "models": {"copy": OPENAI_MODEL, "image": IMAGE_MODEL},
        "dataset_version": DATASET_VERSION,
        "item_count": processed,
        "metrics": {
            "success_rate": round(len(passed) / processed, 3) if processed else 0,
            "clip_score_avg": (
                round(sum(clip_scores) / len(clip_scores), 4) if clip_scores else None
            ),
            "aesthetic_score_avg": (
                round(sum(aesthetic_scores) / len(aesthetic_scores), 4)
                if aesthetic_scores
                else None
            ),
        },
        "items": results,
    }

    out_dir = Path("models/basic/eval/reports")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"image_{datetime.now(UTC).date()}.json"
    out_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"결과 저장: {out_path}")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--limit", type=int, default=20)
    args = parser.parse_args()
    run(args.dataset, args.limit)
