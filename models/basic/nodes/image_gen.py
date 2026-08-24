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
        "실제 거리 현수막처럼 플랫 일러스트/벡터 그래픽 포스터 스타일로 그린다"
        "(사진이 아님). 밝고 단순한 배경(단색 또는 옅은 그라데이션) 위에, "
        "화면 좌우 여백에는 소재와 관련된 아이콘·일러스트 소품을 장식으로 배치한다. "
        "가로로 넓은 배너 레이아웃, 원거리에서도 눈에 띄는 고대비 색상 구성."
    ),
}
_DEFAULT_PLATFORM = "instagram"


def _build_image_prompt(store: dict, copy: str, platform: str | None) -> str:
    """가게 정보·카피·플랫폼을 바탕으로 이미지 생성 프롬프트를 만든다."""
    style = _PLATFORM_IMAGE_STYLE.get(
        platform, _PLATFORM_IMAGE_STYLE[_DEFAULT_PLATFORM]
    )
    prompt = f"{store.get('type', '가게')} 광고 이미지. 소재: {copy}. {style}"

    if platform == "banner":
        prompt += (
            f" 화면 중앙에 다음 한국어 문구를 굵고 큼직한 컬러 타이포그래피로 "
            f'정확한 철자로 표시한다: "{copy}"'
        )
    return prompt


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
            prompts.append(None)
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
                    "error": {
                        "field": "image",
                        "reason": reason,
                        "message": str(exc) or "이미지 생성 중 오류가 발생했습니다.",
                    },
                }
            )
            prompts.append(None)

    return {"ranked_copies": updated, "image_results": images, "image_prompts": prompts}
