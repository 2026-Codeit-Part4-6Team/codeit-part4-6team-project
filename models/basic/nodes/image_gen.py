import openai

from ..clients.image_client import generate_image
from ..graph.state import BasicState


def _classify_image_error(exc: Exception) -> str:
    """이미지 생성 예외를 rate_limit/timeout/content_policy/unknown 사유로 분류한다."""
    if isinstance(exc, openai.RateLimitError):
        return "rate_limit"
    if isinstance(exc, openai.APITimeoutError):
        return "timeout"
    if isinstance(exc, openai.BadRequestError):
        return "content_policy"
    if isinstance(exc, TimeoutError):
        return "timeout"
    return "unknown"


def image_gen_node(state: BasicState) -> dict:
    """랭킹된 카피마다 이미지를 생성해 붙인다. 카피가 없는 항목은 건너뛰고,
    생성 실패 항목은 사유와 함께 image_b64를 None으로 기록한다."""
    store = state["store"]
    updated = []
    images = []
    prompts = []

    for c in state["ranked_copies"]:
        if not c.get("copy"):
            updated.append(c)
            continue

        prompt = (
            f"{store.get('type', '가게')} 광고용 상업 사진. "
            f"소재: {c['copy']}. "
            f"밝고 따뜻한 느낌의 사진 스타일. "
        )
        try:
            image_b64 = generate_image(prompt)
            updated.append({**c, "image_b64": image_b64})
            images.append(image_b64)
            prompts.append(prompt)
        # BLE001 억제 사유: 항목 하나 실패가 배치 전체를 죽이지 않도록 모든 예외를 잡아 개별 에러로 기록
        except Exception as exc:  # noqa: BLE001
            reason = _classify_image_error(exc)
            updated.append(
                {
                    **c,
                    "image_b64": None,
                    "error": {"field": "image", "reason": reason, "message": str(exc)},
                }
            )
            prompts.append(None)

    return {"ranked_copies": updated, "image_results": images, "image_prompts": prompts}
