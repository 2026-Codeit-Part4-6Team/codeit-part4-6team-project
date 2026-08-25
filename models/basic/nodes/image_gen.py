import base64
import io

import openai
from PIL import Image

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

_PLATFORM_IMAGE_SIZE = {
    "instagram": "1024x1024",  # 정사각형
    "xbanner": "1024x1536",  # 세로형 스탠드 배너 (상단·하단 동일 사이즈)
}

_PLATFORM_IMAGE_STYLE = {
    "instagram": (
        "따뜻하고 감성적인 라이프스타일 사진 스타일, 얕은 심도로 "
        "제품이나 인물을 가까이서 담은 구도. 인스타그램 피드에서 시선을 끄는 톤."
    ),
}
_DEFAULT_PLATFORM = "instagram"


def _build_image_prompt(store: dict, copy: str, platform: str | None) -> str:
    """instagram 등 단일 이미지 플랫폼용 프롬프트를 만든다."""
    style = _PLATFORM_IMAGE_STYLE.get(
        platform, _PLATFORM_IMAGE_STYLE[_DEFAULT_PLATFORM]
    )
    return f"{store.get('type', '가게')} 광고 이미지. 소재: {copy}. {style}"


def _build_xbanner_top_prompt(store: dict, copy: str) -> str:
    """X배너 상단부(카피+비주얼) 프롬프트를 만든다."""
    return (
        f"세로형 스탠드 배너(X배너)의 상단부 디자인. 강렬한 그라데이션 배경"
        f"(업종에 어울리는 색상 — {store.get('type', '가게')} 분위기에 맞게). "
        f"화면 상단에 다음 한국어 문구를 크고 임팩트 있는 컬러 타이포그래피로 "
        f'정확한 철자로 표시한다: "{copy}" '
        f"하단부에는 관련 제품·메뉴를 강조한 이미지를 배치한다. "
        f"사진이 아닌 플랫 그래픽 포스터 디자인 스타일. "
        f"배너 거치대나 다리(스탠드 프레임)는 그리지 않는다 — 배너 인쇄면만 표현한다."
    )


def _build_xbanner_bottom_prompt(store: dict) -> str:
    """X배너 하단부(가게 정보) 프롬프트를 만든다. 주어진 정보만 쓰고,
    영업시간·전화번호 등 제공되지 않은 항목은 절대 지어내지 않는다."""
    provided_info = f'상호 "{store.get("name")}", 주소 "{store.get("address")}"'
    return (
        f"세로형 스탠드 배너(X배너)의 하단부 디자인. 밝고 단순한 배경"
        f"(흰색 또는 아주 옅은 색). "
        f"이 디자인은 반드시 \"{store.get('name')}\"이라는 이 가게 하나만을 위한 것이다. "
        f"다른 브랜드명, 로고, 회사명, 업종(예: 병원·상담센터·기타 서비스업)을 "
        f"절대 등장시키지 않는다. "
        f"다음 정보만 깔끔한 타이포그래피로 정리해서 표시한다: {provided_info}. "
        f"위에 나열되지 않은 정보(영업시간, 전화번호, 행사 일정 등)는 "
        f"절대로 임의로 지어내서 표시하지 않는다 — 주어지지 않은 항목은 "
        f"화면에 아예 넣지 않는다. "
        f"위쪽 상단 이미지와 어울리는 색 포인트를 일부 사용하되, "
        f"전체적으로는 정보 전달 위주의 차분한 레이아웃. "
        f"사진이 아닌 플랫 그래픽 포스터 디자인 스타일. "
        f"배너 거치대나 다리(스탠드 프레임)는 그리지 않는다 — 배너 인쇄면만 표현한다."
    )


def _generate_xbanner(store: dict, copy: str) -> str:
    """X배너를 상단(카피+비주얼)/하단(가게 정보) 두 장으로 나눠 생성한 뒤
    세로로 이어붙여 base64 PNG 하나로 반환한다."""
    size = _PLATFORM_IMAGE_SIZE["xbanner"]

    top_b64 = generate_image(_build_xbanner_top_prompt(store, copy), size=size)
    top_img = Image.open(io.BytesIO(base64.b64decode(top_b64)))

    bottom_b64 = generate_image(_build_xbanner_bottom_prompt(store), size=size)
    bottom_img = Image.open(io.BytesIO(base64.b64decode(bottom_b64)))

    width = max(top_img.width, bottom_img.width)
    combined = Image.new("RGB", (width, top_img.height + bottom_img.height))
    combined.paste(top_img, (0, 0))
    combined.paste(bottom_img, (0, top_img.height))

    buffer = io.BytesIO()
    combined.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode()


def image_gen_node(state: BasicState) -> dict:
    """랭킹된 카피마다 이미지를 생성해 붙인다. 카피가 없는 항목은 건너뛰고,
    생성 실패 항목은 사유와 함께 image_b64를 None으로 기록한다. xbanner
    플랫폼은 상단(카피+비주얼)/하단(가게 정보) 두 장을 생성해 세로로
    이어붙인 결과를 사용한다."""
    store = state["store"]
    platform = state.get("platform")
    updated = []
    images = []
    prompts = []

    for c in state["ranked_copies"]:
        if not c.get("copy"):
            updated.append(c)
            prompts.append(None)
            continue

        try:
            if platform == "xbanner":
                image_b64 = _generate_xbanner(store, c["copy"])
                prompt_record = _build_xbanner_top_prompt(store, c["copy"])
            else:
                size = _PLATFORM_IMAGE_SIZE.get(
                    platform, _PLATFORM_IMAGE_SIZE[_DEFAULT_PLATFORM]
                )
                prompt_record = _build_image_prompt(store, c["copy"], platform)
                image_b64 = generate_image(prompt_record, size=size)

            updated.append({**c, "image_b64": image_b64})
            images.append(image_b64)
            prompts.append(prompt_record)
        # BLE001 억제 사유: 항목 하나 실패가 배치 전체를 죽이지 않도록 모든 예외를 잡아 개별 에러로 기록
        except Exception as exc:  # noqa: BLE001
            reason = _classify_image_error(exc)
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
