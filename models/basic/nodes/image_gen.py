from ..clients.image_client import generate_image
from ..graph.state import BasicState
from ..llm_errors import classify_image_error

_PLATFORM_IMAGE_SIZE = {
    "instagram": "1024x1024",  # 정사각형
    "banner": "1536x1024",  # 가로형
}

_PLATFORM_IMAGE_STYLE = {
    "instagram": (
        "따뜻하고 감성적인 라이프스타일 사진 스타일, 얕은 심도로 "
        "제품이나 인물을 가까이서 담은 구도. 인스타그램 피드에서 시선을 끄는 톤."
    ),
    "banner": (
        "선명하고 눈에 띄는 상업 광고 사진 스타일. 배경을 단순하게 정리해 "
        "문구를 얹을 여백을 확보하고, 원거리에서도 알아볼 수 있도록 "
        "고대비·고채도로 표현."
    ),
}
_DEFAULT_PLATFORM = "instagram"


def _build_image_prompt(store: dict, copy: str, platform: str | None) -> str:
    """가게 정보·카피·플랫폼을 바탕으로 이미지 생성 프롬프트를 만든다."""
    style = _PLATFORM_IMAGE_STYLE.get(
        platform, _PLATFORM_IMAGE_STYLE[_DEFAULT_PLATFORM]
    )
    return f"{store.get('type', '가게')} 광고용 상업 사진. 소재: {copy}. {style}"


def image_gen_node(state: BasicState) -> dict:
    """랭킹된 카피마다 이미지를 생성해 붙인다. 카피가 없는 항목은 건너뛰고,
    생성 실패 항목은 사유와 함께 image_b64를 None으로 기록한다."""
    store = state["store"]
    platform = state.get("platform")
    size = _PLATFORM_IMAGE_SIZE.get(platform, _PLATFORM_IMAGE_SIZE[_DEFAULT_PLATFORM])
    updated = []
    images = []
    prompts = []

    for c in state["ranked_copies"]:
        if not c.get("copy"):
            updated.append(c)
            continue

        prompt = _build_image_prompt(store, c["copy"], platform)
        try:
            image_b64 = generate_image(prompt, size=size)
            updated.append({**c, "image_b64": image_b64})
            images.append(image_b64)
            prompts.append(prompt)
        # BLE001 억제 사유: 항목 하나 실패가 배치 전체를 죽이지 않도록 모든 예외를 잡아 개별 에러로 기록
        except Exception as exc:  # noqa: BLE001
            reason = classify_image_error(exc)
            updated.append(
                {
                    **c,
                    "image_b64": None,
                    "error": {"field": "image", "reason": reason, "message": str(exc)},
                }
            )
            prompts.append(None)

    return {"ranked_copies": updated, "image_results": images, "image_prompts": prompts}
