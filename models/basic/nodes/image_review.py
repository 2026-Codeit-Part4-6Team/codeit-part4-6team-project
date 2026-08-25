import base64
import io

import torch
from PIL import Image
from transformers import CLIPModel, CLIPProcessor

from ..graph.state import REASON_UNKNOWN, BasicState

# 참고용 임계값 — MVP에서는 미적용
# 실측 근거(영문 캡션 5쌍): 정답 평균 0.3468 통과 / 오답 평균 0.2185 차단.
# 여유 각각 +0.0968 / -0.0315. 표본이 작아 지금은 적용하지 않고 근거로만 남긴다.
MIN_CLIP_SCORE = 0.25 

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

    MVP 정책: 이미지가 없거나 CLIP 점수가 낮아도 차단하지 않는다. 디코딩 자체가
    전부 실패한 경우만 실제 처리 오류로 보고 재생성을 요청한다. CLIP 점수는
    ranked_copies 항목에는 붙이지 않고 image_review_result에 리스트로만
    남긴다. image_prompt는 image_gen이 항목과 같은 순서로 넘겨준
    image_prompts 리스트에서 인덱스로 짝을 맞춰 읽는다.
    """
    reviewed = []
    clip_scores = []
    has_copy_count = 0
    decode_fail_count = 0
    prompts = state.get("image_prompts") or []
    captions_en = state.get("image_captions_en") or []

    for i, c in enumerate(state["ranked_copies"]):
        if not c.get("copy"):
            reviewed.append(c)
            continue

        has_copy_count += 1

        if not c.get("image_b64"):
            reviewed.append(c)
            continue

        caption = captions_en[i] if i < len(captions_en) else None
        prompt = prompts[i] if i < len(prompts) else None
        text_for_clip = caption or prompt or c["copy"]

        try:
            image = Image.open(io.BytesIO(base64.b64decode(c["image_b64"])))
            score = _clip_score(image, text_for_clip)
        # BLE001 억제 사유: 디코딩/CLIP 추론 중 어떤 예외가 나든 해당 항목만 실패 처리
        except Exception:  # noqa: BLE001
            decode_fail_count += 1
            reviewed.append(
                {
                    **c,
                    "image_b64": None,
                    "error": {
                        "field": "image",
                        "reason": REASON_UNKNOWN,
                        "message": "이미지 디코딩에 실패했습니다.",
                    },
                }
            )
            continue

        clip_scores.append(score)
        reviewed.append(c)

    all_decode_failed = has_copy_count > 0 and decode_fail_count == has_copy_count

    if all_decode_failed:
        return {
            "ranked_copies": reviewed,
            "image_review_result": {"action": "reject", "clip_scores": clip_scores},
            "image_retry_count": state.get("image_retry_count", 0) + 1,
        }

    return {
        "ranked_copies": reviewed,
        "image_review_result": {"action": "pass", "clip_scores": clip_scores},
    }
