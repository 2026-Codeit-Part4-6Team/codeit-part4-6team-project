import openai

from models.shared.llm import call_llm

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


def _build_image_prompt(store: dict, copy: str) -> str:
    """이미지 생성 API에 보낼 한글 프롬프트를 만든다."""
    return (
        f"{store.get('type', '가게')} 광고용 상업 사진. "
        f"소재: {copy}. "
        f"밝고 따뜻한 느낌의 사진 스타일. "
    )


def _english_caption(store_type: str, copy: str) -> str | None:
    """CLIP 채점용 영문 캡션을 만든다(CLIP은 영어 전용이라 한국어로
    채점하면 점수가 무작위에 가깝다). 실패해도 이미지 생성 자체는 막지 않고
    None을 반환해 호출부가 한국어 폴백을 쓰게 한다."""
    try:
        raw, _tokens = call_llm(
            "주어진 광고 카피의 이미지 내용을 설명하는 영어 캡션 한 문장을 만든다. "
            "캡션만 답한다.",
            f"업종: {store_type}\n카피: {copy}",
        )
        return raw.strip()
    # BLE001 억제 사유: 캡션 생성 실패는 CLIP 채점 정확도만 낮출 뿐 파이프라인을 막을 이유가 아님
    except Exception:  # noqa: BLE001
        return None


def image_gen_node(state: BasicState) -> dict:
    """랭킹된 카피마다 이미지를 생성해 붙인다. 카피가 없는 항목은 건너뛰고,
    생성 실패 항목은 사유와 함께 image_b64를 None으로 기록한다.

    image_prompts·image_captions_en은 ranked_copies와 항상 같은 길이, 순서를
    유지한다.
    """
    store = state["store"]
    updated = []
    images = []
    prompts = []
    captions_en = []

    for c in state["ranked_copies"]:
        if not c.get("copy"):
            updated.append(c)
            prompts.append(None)
            captions_en.append(None)
            continue

        prompt = _build_image_prompt(store, c["copy"])
        try:
            image_b64 = generate_image(prompt)
            updated.append({**c, "image_b64": image_b64})
            images.append(image_b64)
            prompts.append(prompt)
            captions_en.append(_english_caption(store.get("type", "store"), c["copy"]))
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
            captions_en.append(None)

    return {
        "ranked_copies": updated,
        "image_results": images,
        "image_prompts": prompts,
        "image_captions_en": captions_en,
    }
