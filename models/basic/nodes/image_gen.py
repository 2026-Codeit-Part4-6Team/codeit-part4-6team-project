import base64
import io

import openai
from PIL import Image

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

_PLATFORM_IMAGE_SIZE = {
    "instagram": "1024x1024",  # 정사각형
    "xbanner": "1024x1536",  # 세로형 스탠드 배너 (상단·하단 동일 사이즈)
}

_PLATFORM_IMAGE_PROMPT = {
    "instagram_hero_product": (
        "{store_type} 광고 이미지. 제품/메뉴 1개를 화면 중앙 또는 풀스크린에 "
        "크고 선명하게 배치한다. 이미지 상단에는 다음 문구 중 가장 핵심적인 "
        "한 줄만 크고 임팩트 있는 타이포그래피로 얹는다: \"{copy}\" "
        "할인·가격·혜택 정보가 문구에 있으면 우측 하단이나 코너에 작은 "
        "배너/스티커 형태로 별도 배치한다. 배경은 단순하게 정리해 제품에 "
        "시선이 집중되게 한다. 인스타그램 피드에서 시선을 끄는 선명한 톤."
        "이미지에는 해시태그를 포함시키지 않는다."
    ),
    "instagram_character": (
        "{store_type} 광고 이미지. 귀엽고 개성 있는 AI 캐릭터(인스타툰 스타일) "
        "1명이 등장해 제품을 자연스럽게 들고 있거나 소개하는 장면. "
        "캐릭터의 대사나 표정으로 다음 문구의 분위기를 전달한다: \"{copy}\" "
        "실제 사진이 아닌 귀여운 일러스트/웹툰 캐릭터 스타일. "
        "브랜드 컬러를 캐릭터 의상이나 소품에 살짝 반영한다."
        "이미지에는 해시태그를 포함시키지 않는다."
    ),
    "instagram_meme": (
        "{store_type} 광고 이미지. 밈(meme) 스타일 — MZ세대 타겟. "
        "고객이 겪을 법한 불편한 상황을 과장된 표정의 캐릭터/짤 형태로 표현하고, "
        "그 위에 말풍선 또는 자막 텍스트로 고객의 속마음을 짧고 재치있게 적는다: "
        "\"{copy}\"를 참고해 소재를 잡되 그대로 옮기지 말고 상황극으로 재구성한다. "
        "실제 인터넷 밈 캡처가 아니라 AI가 새로 그린 일러스트/캐릭터 스타일로 만든다. "
        "정색체가 아닌 유머러스하고 과장된 톤."
        "이미지에는 해시태그를 포함시키지 않는다."
    ),
    "instagram_chat_mockup": (
        "{store_type} 광고 이미지. 스마트폰 메신저 대화창을 캡처한 것처럼 "
        "디자인한다. 위쪽 말풍선엔 고객이 겪을 법한 질문/고민을 짧게 적고, "
        "아래쪽 답변 말풍선엔 이모티콘과 함께 제품 이미지를 작게 배치해 "
        "답변처럼 보이게 한다. 다음 문구의 핵심을 답변 톤에 반영한다: \"{copy}\" "
        "실제 메신저 앱 UI(말풍선·시간 표시·프로필 아이콘)를 참고한 목업 스타일."
        "이미지에는 해시태그를 포함시키지 않는다."
    ),
    "xbanner_top": (
        "세로형 스탠드 배너(X배너)의 상단부 디자인. 업종에 어울리는 색상 배경"
        "(업종에 어울리는 색상 — {store_type} 분위기에 맞게). "
        "화면 상단에 다음 한국어 문구를 크고 임팩트 있는 컬러 타이포그래피로 "
        '정확한 철자로 표시한다: "{copy}" '
        "하단부에는 관련 제품·메뉴를 강조한 이미지를 배치한다. "
        "사진이 아닌 플랫 그래픽 포스터 디자인 스타일. "
        "배너 거치대나 다리(스탠드 프레임)는 그리지 않는다 — 배너 인쇄면만 표현한다."
    ),
    "xbanner_bottom": (
        "세로형 스탠드 배너(X배너)의 하단부 디자인. 밝고 단순한 배경"
        "(상단부와 비슷한 계열의 색상). "
        '이 디자인은 반드시 "{store_name}"이라는 이 가게 하나만을 위한 것이다. '
        "다른 브랜드명, 로고, 회사명, 업종(예: 병원·상담센터·기타 서비스업)을 "
        "절대 등장시키지 않는다. "
        "다음 정보만 깔끔한 타이포그래피로 정리해서 표시한다: {provided_info}. "
        "위에 나열되지 않은 정보(영업시간, 전화번호, 행사 일정 등)는 "
        "절대로 임의로 지어내서 표시하지 않는다 — 주어지지 않은 항목은 "
        "화면에 아예 넣지 않는다. "
        "다음 문구에 할인·이벤트·프로모션 등 구체적인 혜택 내용이 있다면, "
        "그 내용만 작은 배너나 스티커 형태로 하단부에 강조해서 표시한다: "
        '"{copy}" (혜택 내용이 없으면 이 부분은 생략한다). '
        "화면 하단에 여백이 넓게 남지 않도록, 도형·패턴 같은 장식 "
        "요소로 균형 있게 채운다. "
        "위쪽 상단 이미지와 어울리는 색 포인트를 일부 사용하되, "
        "전체적으로는 정보 전달 위주의 차분한 레이아웃. "
        "사진이 아닌 플랫 그래픽 포스터 디자인 스타일. "
        "배너 거치대나 다리(스탠드 프레임)는 그리지 않는다 — 배너 인쇄면만 표현한다."
    ),
}
_DEFAULT_PLATFORM = "instagram"

# 트렌드에 민감한 라이프스타일/뷰티 업종은 밈이, 그 외 생활 밀착형 업종은
# 메신저 목업(바로 궁금한 걸 답해주는 형태)이 더 적합하다고 보고 나눈다.
_MEME_SUITABLE_TYPES = {"카페", "네일샵", "헤어샵", "펫살롱", "디저트", "베이커리"}


def _pick_instagram_template(store: dict, index: int) -> str:
    """카피 3개 중 1번은 hero_product, 2번은 character로 고정하고,
    3번은 업종에 맞춰 meme/chat_mockup 중 더 적합한 쪽을 고른다."""
    if index == 0:
        return _PLATFORM_IMAGE_PROMPT["instagram_hero_product"]
    if index == 1:
        return _PLATFORM_IMAGE_PROMPT["instagram_character"]
    key = (
        "instagram_meme"
        if store.get("type", "") in _MEME_SUITABLE_TYPES
        else "instagram_chat_mockup"
    )
    return _PLATFORM_IMAGE_PROMPT[key]


def _generate_xbanner(store: dict, copy: str) -> str:
    """X배너를 상단(카피+비주얼)/하단(가게 정보+혜택 강조) 두 장으로 나눠 생성한 뒤
    세로로 이어붙여 base64 PNG 하나로 반환한다."""
    size = _PLATFORM_IMAGE_SIZE["xbanner"]

    top_prompt = _PLATFORM_IMAGE_PROMPT["xbanner_top"].format(
        store_type=store.get("type", "가게"), copy=copy
    )
    top_b64 = generate_image(top_prompt, size=size)
    top_img = Image.open(io.BytesIO(base64.b64decode(top_b64)))

    provided_info = f'상호 "{store.get("name")}", 주소 "{store.get("address")}"'
    bottom_prompt = _PLATFORM_IMAGE_PROMPT["xbanner_bottom"].format(
        store_name=store.get("name"), provided_info=provided_info, copy=copy
    )
    bottom_b64 = generate_image(bottom_prompt, size=size)
    bottom_img = Image.open(io.BytesIO(base64.b64decode(bottom_b64)))

    width = max(top_img.width, bottom_img.width)
    combined = Image.new("RGB", (width, top_img.height + bottom_img.height))
    combined.paste(top_img, (0, 0))
    combined.paste(bottom_img, (0, top_img.height))

    buffer = io.BytesIO()
    combined.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode()


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
    생성 실패 항목은 사유와 함께 image_b64를 None으로 기록한다. xbanner
    플랫폼은 상단(카피+비주얼)/하단(가게 정보) 두 장을 생성해 세로로
    이어붙인 결과를 사용한다."""
    store = state["store"]
    platform = state.get("platform")
    updated = []
    images = []
    prompts = []
    captions_en = []

    for i, c in enumerate(state["ranked_copies"]):
        if not c.get("copy"):
            updated.append(c)
            prompts.append(None)
            captions_en.append(None)
            continue

        try:
            if platform == "xbanner":
                image_b64 = _generate_xbanner(store, c["copy"])
                prompt_record = _PLATFORM_IMAGE_PROMPT["xbanner_top"].format(
                    store_type=store.get("type", "가게"), copy=c["copy"]
                )
            else:
                size = _PLATFORM_IMAGE_SIZE.get(
                    platform, _PLATFORM_IMAGE_SIZE[_DEFAULT_PLATFORM]
                )
                template = _pick_instagram_template(store, i)
                prompt_record = template.format(
                    store_type=store.get("type", "가게"), copy=c["copy"]
                )
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
            captions_en.append(None)
    return {
        "ranked_copies": updated,
        "image_results": images,
        "image_prompts": prompts,
        "image_captions_en": captions_en,
    }
