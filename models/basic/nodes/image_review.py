import base64
import io

import torch
from PIL import Image
from transformers import CLIPModel, CLIPProcessor

from ..graph.state import BasicState

MIN_CLIP_SCORE = 0.25  # 임시값 - 골든 데이터셋으로 튜닝 필요

_clip_model = None
_clip_processor = None


def _load_clip():
    """CLIP 모델과 프로세서를 지연 로드하여 캐싱한다."""
    global _clip_model, _clip_processor
    if _clip_model is None:
        _clip_model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
        _clip_processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
    return _clip_model, _clip_processor


def preload_clip():
    """앱 기동 시 CLIP 가중치를 미리 받아 첫 요청의 지연을 제거합니다."""
    _load_clip()


def _clip_score(image, text: str) -> float:
    """이미지와 텍스트 간 CLIP 코사인 유사도 점수를 계산한다."""
    model, processor = _load_clip()
    inputs = processor(text=[text], images=image, return_tensors="pt", padding=True)
    with torch.no_grad():
        outputs = model(**inputs)
    image_embeds = outputs.image_embeds / outputs.image_embeds.norm(
        dim=-1, keepdim=True
    )
    text_embeds = outputs.text_embeds / outputs.text_embeds.norm(dim=-1, keepdim=True)
    return (image_embeds @ text_embeds.T).item()


def image_review_node(state: BasicState) -> dict:
    """생성된 이미지를 디코딩해 CLIP 적합도 점수로 검수한다. 디코딩 실패나
    기준 점수 미달 항목은 반려 처리하고, 모든 항목이 실패하면 재생성을 요청한다."""
    reviewed = []
    has_copy_count = 0
    image_fail_count = 0

    for c in state["ranked_copies"]:
        if not c.get("copy"):
            reviewed.append(c)
            continue

        has_copy_count += 1

        if not c.get("image_b64"):
            image_fail_count += 1
            reviewed.append(c)
            continue

        try:
            image = Image.open(io.BytesIO(base64.b64decode(c["image_b64"])))
            score = _clip_score(image, c.get("image_prompt", c["copy"]))
        # BLE001 억제 사유: 디코딩/CLIP 추론 중 어떤 예외가 나든 해당 항목만 실패 처리
        except Exception:  # noqa: BLE001
            image_fail_count += 1
            reviewed.append(
                {
                    **c,
                    "image_b64": None,
                    "error": {
                        "field": "image",
                        "reason": "decode_failed",
                        "message": "이미지 디코딩에 실패했습니다.",
                    },
                }
            )
            continue

        if score < MIN_CLIP_SCORE:
            image_fail_count += 1
            reviewed.append(
                {
                    **c,
                    "image_b64": None,
                    "error": {
                        "field": "image",
                        "reason": "low_clip_score",
                        "message": f"이미지 적합도 점수가 낮습니다({score:.2f}).",
                    },
                }
            )
            continue

        reviewed.append({**c, "clip_score": score})

    all_failed = has_copy_count > 0 and image_fail_count == has_copy_count

    if all_failed:
        return {
            "ranked_copies": reviewed,
            "image_review_result": {"action": "reject"},
            "retry_count": state.get("retry_count", 0) + 1,
        }

    return {
        "ranked_copies": reviewed,
        "image_review_result": {"action": "pass"},
    }
