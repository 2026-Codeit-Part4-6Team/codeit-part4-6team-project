import base64
import io

import torch
from PIL import Image
from transformers import CLIPModel, CLIPProcessor

from ..graph.state import BasicState

MIN_CLIP_SCORE = 0.25  # 참고용 임계값 — MVP에서는 미적용

_clip_model = None
_clip_processor = None


def _load_clip():
    """CLIP 모델과 프로세서를 지연 로드하여 캐싱한다."""
    global _clip_model, _clip_processor
    if _clip_model is None:
        _clip_model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
        _clip_processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
    return _clip_model, _clip_processor


def _clip_score(image, text: str) -> float:
    """이미지와 텍스트 간 CLIP 코사인 유사도 점수를 계산한다."""
    model, processor = _load_clip()
    inputs = processor(
        text=[text],
        images=image,
        return_tensors="pt",
        padding=True,
        truncation=True,
        max_length=77,
    )
    with torch.no_grad():
        outputs = model(**inputs)
    image_embeds = outputs.image_embeds / outputs.image_embeds.norm(
        dim=-1, keepdim=True
    )
    text_embeds = outputs.text_embeds / outputs.text_embeds.norm(dim=-1, keepdim=True)
    return (image_embeds @ text_embeds.T).item()


def image_review_node(state: BasicState) -> dict:
    """생성된 이미지를 디코딩해 CLIP 적합도 점수를 기록한다.

    MVP 정책: 이미지가 없거나 CLIP 점수가 낮아도 차단하지 않는다(CLIP Score는
    현재 개발용 평가 지표일 뿐 — FR-13b). 디코딩 자체가 전부 실패한 경우만
    실제 처리 오류로 보고 재생성을 요청한다.
    """
    reviewed = []
    has_copy_count = 0
    decode_fail_count = 0

    for c in state["ranked_copies"]:
        if not c.get("copy"):
            reviewed.append(c)
            continue

        has_copy_count += 1

        if not c.get("image_b64"):
            reviewed.append(c)
            continue

        try:
            image = Image.open(io.BytesIO(base64.b64decode(c["image_b64"])))
            score = _clip_score(image, c.get("image_prompt", c["copy"]))
        # BLE001 억제 사유: 디코딩/CLIP 추론 중 어떤 예외가 나든 해당 항목만 실패 처리
        except Exception:  # noqa: BLE001
            decode_fail_count += 1
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

        reviewed.append({**c, "clip_score": score})

    all_decode_failed = has_copy_count > 0 and decode_fail_count == has_copy_count

    if all_decode_failed:
        return {
            "ranked_copies": reviewed,
            "image_review_result": {"action": "reject"},
            "image_retry_count": state.get("image_retry_count", 0) + 1,
        }

    return {
        "ranked_copies": reviewed,
        "image_review_result": {"action": "pass"},
    }
