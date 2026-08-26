import base64
import io
import re

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


_BENEFIT_KEYWORDS = (
    "할인",
    "무료",
    "공짜",
    "이벤트",
    "프로모션",
    "특가",
    "1+1",
    "2+1",
    "%",
    "사은품",
    "증정",
    "쿠폰",
    "세일",
    "적립",
)


_COMMON_IMAGE_RULES = (
    "할인·무료·증정 문구를 넣을 때는 조건을 반드시 함께 적는다 — "
    '"한 잔 무료"가 아니라 "두 잔 구매 시 한 잔 무료"처럼 조건과 묶어서 '
    "표시한다. "
    "화면에 넣는 한국어는 큰 글씨 위주로 하고, 작은 보조 문구·뱃지·라벨은 "
    "최소화한다 — 작은 글씨에서 한글이 깨지는 문제가 실측으로 확인됐다."
    "주어진 카피·정보에 없는 내용(혜택, 가격, 기간, 상호·주소 외 연락처 등)을 "
    "새로 만들어 넣지 않는다 — 화면이 허전해 보여도 없는 정보를 채우지 않는다. "
)


def _split_benefit_clause(copy: str) -> tuple[str, str | None]:
    """카피를 문장 단위로 나눠, 할인·무료·이벤트 등 혜택 키워드가 포함된
    문장은 하단 배너용으로, 나머지(가게 자체 소개)는 상단 배너용으로
    분리한다. 혜택 문장이 없으면 전체를 상단에 쓰고 하단은 None을
    반환해 스티커 자체를 생략하게 한다. 이미지 생성 모델에게 '일부만
    추출'을 맡기면 상단 문구를 하단에 그대로 반복하는 문제가 실측으로
    확인되어, 텍스트 단계에서 파이썬으로 미리 나눈다."""
    clauses = [c.strip() for c in re.split(r"(?<=[!.?~])\s+", copy) if c.strip()]
    benefit = [c for c in clauses if any(k in c for k in _BENEFIT_KEYWORDS)]
    rest = [c for c in clauses if c not in benefit]
    top_text = " ".join(rest) if rest else copy
    bottom_text = " ".join(benefit) if benefit else None
    return top_text, bottom_text


_PLATFORM_IMAGE_SIZE = {
    "instagram": "1024x1024",  # 정사각형
    "xbanner": "1024x1536",  # 세로형 스탠드 배너 (상단·하단 동일 사이즈)
}

_PLATFORM_IMAGE_PROMPT = {
    "instagram_hero_product": (
        "{store_type} 광고 이미지. 제품/메뉴 1개를 화면 중앙 또는 풀스크린에 "
        "크고 선명하게 배치한다. 이미지 상단에는 다음 문구 중 가장 핵심적인 "
        '한 줄만 크고 임팩트 있는 타이포그래피로 얹는다: "{copy}" '
        "할인·가격·혜택 정보가 문구에 있으면 우측 하단이나 코너에 작은 "
        "배너/스티커 형태로 별도 배치한다. 배경은 단순하게 정리해 제품에 "
        "시선이 집중되게 한다. 인스타그램 피드에서 시선을 끄는 선명한 톤. "
        "문구에 없는 할인율·이벤트명·상품명을 새로 만들어 넣지 않는다. "
        "이미지에는 해시태그를 포함시키지 않는다."
    )
    + _COMMON_IMAGE_RULES,
    "instagram_character": (
        "{store_type} 광고 이미지. 귀엽고 개성 있는 AI 캐릭터"
        "(인스타툰 스타일의 사람이나 동물 캐릭터) "
        "가 등장해 제품을 자연스럽게 들고 있거나 소개하는 장면. "
        '캐릭터의 대사나 표정으로 다음 문구의 분위기를 전달한다: "{copy}" '
        "실제 사진이 아닌 귀여운 일러스트/웹툰 캐릭터 스타일. "
        "브랜드 컬러를 캐릭터 의상이나 소품에 살짝 반영한다."
        "문구에 없는 할인율·이벤트명·상품명을 새로 만들어 넣지 않는다. "
        "이미지에는 해시태그를 포함시키지 않는다."
    )
    + _COMMON_IMAGE_RULES,
    "instagram_meme": (
        "{store_type} 광고 이미지. 밈(meme) 스타일 — MZ세대 타겟. "
        "고객이 겪을 법한 불편한 상황을 과장된 표정의 캐릭터/짤 형태로 표현하고, "
        "그 위에 말풍선 또는 자막 텍스트로 고객의 속마음을 짧고 재치있게 적는다: "
        '"{copy}"를 참고해 소재를 잡되 그대로 옮기지 말고 상황극으로 재구성한다. '
        "실제 인터넷 밈 캡처가 아니라 AI가 새로 그린 일러스트/캐릭터 스타일로 만든다. "
        "정색체가 아닌 유머러스하고 과장된 톤."
        "말풍선·자막에 문구에 없는 할인율·이벤트명 등 구체적 수치를 새로 "
        "지어내지 않는다. "
        "이미지에는 해시태그를 포함시키지 않는다."
    )
    + _COMMON_IMAGE_RULES,
    "xbanner_top_picture": (
        "세로형 스탠드 배너(X배너)의 상단부 디자인. 업종에 어울리는 색상 배경"
        "(업종에 어울리는 색상 — {store_type} 분위기에 맞게). "
        "화면 상단에 다음 한국어 문구를 크고 임팩트 있는 컬러 타이포그래피로 "
        '할인·이벤트·프로모션의 구체적인 내용을 제외한 핵심 내용을 표시한다: "{copy}" '
        "카피에 없는 할인율·상품명·이벤트명 등을 새로 만들어 넣지 않는다. "
        "하단부에는 관련 제품·메뉴를 강조한 이미지를 배치한다. "
        "실제 사진처럼 보이는 상업 사진 스타일. 제품·메뉴 사진을 중심에 두고 "
        "자연스러운 조명과 구도로 촬영한 느낌을 낸다. "
        "배너 거치대나 다리(스탠드 프레임)는 그리지 않는다 — 배너 인쇄면만 표현한다."
    )
    + _COMMON_IMAGE_RULES,
    "xbanner_top_flat": (
        "세로형 스탠드 배너(X배너)의 상단부 디자인. 업종에 어울리는 색상 배경"
        "(업종에 어울리는 색상 — {store_type} 분위기에 맞게). "
        "화면 상단에 다음 한국어 문구를 크고 임팩트 있는 컬러 타이포그래피로 "
        '할인·이벤트·프로모션의 구체적인 내용을 제외한 핵심 내용을 표시한다: "{copy}" '
        "카피에 없는 할인율·상품명·이벤트명 등을 새로 만들어 넣지 않는다. "
        "하단부에는 관련 제품·메뉴를 강조한 이미지를 배치한다. "
        "사진이 아닌 플랫 그래픽 포스터 디자인 스타일. 단순화된 일러스트와 "
        "도형·패턴으로 구성한다. "
        "배너 거치대나 다리(스탠드 프레임)는 그리지 않는다 — 배너 인쇄면만 표현한다."
    )
    + _COMMON_IMAGE_RULES,
    "xbanner_top_typography": (
        "세로형 스탠드 배너(X배너)의 상단부 디자인. 업종에 어울리는 색상 배경"
        "(업종에 어울리는 색상 — {store_type} 분위기에 맞게). "
        "화면 상단에 다음 한국어 문구를 크고 임팩트 있는 컬러 타이포그래피로 "
        '할인·이벤트·프로모션의 구체적인 내용을 제외한 핵심 내용을 표시한다: "{copy}" '
        "카피에 없는 할인율·상품명·이벤트명 등을 새로 만들어 넣지 않는다. "
        "문구 자체가 화면의 주인공이 되도록 크고 강렬한 타이포그래피를 "
        "중심에 배치하고, 배경은 단색이나 그라데이션으로 단순하게 유지한다. "
        "제품·메뉴는 사진이 아니라 작은 스티커 느낌의 아이콘이나 플랫 "
        "그래픽 일러스트로, 문구를 가리지 않는 구석 자리에 포인트로만 "
        "곁들인다. "
        "배너 거치대나 다리(스탠드 프레임)는 그리지 않는다 — 배너 인쇄면만 표현한다."
    )
    + _COMMON_IMAGE_RULES,
    "xbanner_bottom_picture": (
        "세로형 스탠드 배너(X배너)의 하단부 디자인. 밝고 단순한 배경"
        "(상단부와 비슷한 계열의 색상). "
        '이 디자인은 반드시 "{store_name}"이라는 이 가게 하나만을 위한 것이다. '
        "다른 브랜드명, 로고, 회사명, 업종(예: 병원·상담센터·기타 서비스업)을 "
        "절대 등장시키지 않는다. "
        "화면 위쪽(상단)에 배치한다: {benefit_clause} "
        "그 아래(화면 하단)에 다음 정보만 깔끔한 타이포그래피로 정리해서 "
        "표시한다: {provided_info}. 위에 나열되지 않은 정보(영업시간, 전화번호, "
        "행사 일정 등)는 절대로 임의로 지어내서 표시하지 않는다 — 주어지지 "
        "않은 항목은 화면에 아예 넣지 않는다. "
        "화면 하단에 여백이 넓게 남지 않도록, 도형·패턴 같은 장식 "
        "요소로 균형 있게 채운다. "
        "위쪽 상단 이미지와 어울리는 색 포인트를 일부 사용하되, "
        "전체적으로는 정보 전달 위주의 차분한 레이아웃. "
        "실제 사진처럼 보이는 상업 사진 스타일로, 상단부와 어울리는 소품 "
        "사진을 작게 곁들인다. "
        "배너 거치대나 다리(스탠드 프레임)는 그리지 않는다 — 배너 인쇄면만 표현한다."
    )
    + _COMMON_IMAGE_RULES,
    "xbanner_bottom_flat": (
        "세로형 스탠드 배너(X배너)의 하단부 디자인. 밝고 단순한 배경"
        "(상단부와 비슷한 계열의 색상). "
        '이 디자인은 반드시 "{store_name}"이라는 이 가게 하나만을 위한 것이다. '
        "다른 브랜드명, 로고, 회사명, 업종(예: 병원·상담센터·기타 서비스업)을 "
        "절대 등장시키지 않는다. "
        "화면 위쪽(상단)에 배치한다: {benefit_clause} "
        "그 아래(화면 하단)에 다음 정보만 깔끔한 타이포그래피로 정리해서 "
        "표시한다: {provided_info}. 위에 나열되지 않은 정보(영업시간, 전화번호, "
        "행사 일정 등)는 절대로 임의로 지어내서 표시하지 않는다 — 주어지지 "
        "않은 항목은 화면에 아예 넣지 않는다. "
        "화면 하단에 여백이 넓게 남지 않도록, 도형·패턴 같은 장식 "
        "요소로 균형 있게 채운다. "
        "위쪽 상단 이미지와 어울리는 색 포인트를 일부 사용하되, "
        "전체적으로는 정보 전달 위주의 차분한 레이아웃. "
        "사진이 아닌 플랫 그래픽/일러스트 기반으로 표현한다. "
        "배너 거치대나 다리(스탠드 프레임)는 그리지 않는다 — 배너 인쇄면만 표현한다."
    )
    + _COMMON_IMAGE_RULES,
    "xbanner_bottom_typography": (
        "세로형 스탠드 배너(X배너)의 하단부 디자인. 밝고 단순한 배경"
        "(상단부와 비슷한 계열의 색상). "
        '이 디자인은 반드시 "{store_name}"이라는 이 가게 하나만을 위한 것이다. '
        "다른 브랜드명, 로고, 회사명, 업종(예: 병원·상담센터·기타 서비스업)을 "
        "절대 등장시키지 않는다. "
        "화면 위쪽(상단)에 배치한다: {benefit_clause} "
        "그 아래(화면 하단)에 다음 정보만 깔끔한 타이포그래피로 정리해서 "
        "표시한다: {provided_info}. 위에 나열되지 않은 정보(영업시간, 전화번호, "
        "행사 일정 등)는 절대로 임의로 지어내서 표시하지 않는다 — 주어지지 "
        "않은 항목은 화면에 아예 넣지 않는다. "
        "화면 하단에 여백이 넓게 남지 않도록, 도형·패턴 같은 장식 "
        "요소로 균형 있게 채운다. "
        "위쪽 상단 이미지와 어울리는 색 포인트를 일부 사용하되, "
        "전체적으로는 정보 전달 위주의 차분한 레이아웃. "
        "사진이 아니라, 상단부와 같은 강렬한 타이포그래피를 중심으로 하되 "
        "작은 스티커 느낌의 아이콘이나 플랫 그래픽 요소를 구석에 포인트로 "
        "곁들인다. "
        "배너 거치대나 다리(스탠드 프레임)는 그리지 않는다 — 배너 인쇄면만 표현한다."
    )
    + _COMMON_IMAGE_RULES,
}
_DEFAULT_PLATFORM = "instagram"


def _pick_xbanner_template(index: int) -> tuple[str, str]:
    """카피 후보 인덱스에 따라 상단/하단 스타일(사진/플랫 그래픽/타이포그래피)을
    같은 조합으로 짝지어 반환한다."""
    variants = [
        ("xbanner_top_picture", "xbanner_bottom_picture"),
        ("xbanner_top_flat", "xbanner_bottom_flat"),
        ("xbanner_top_typography", "xbanner_bottom_typography"),
    ]
    return variants[index % len(variants)]


def _pick_instagram_template(store: dict, index: int) -> str:
    """카피 3개를 순서대로 hero_product → character → meme에 고정 배정한다."""
    keys = ["instagram_hero_product", "instagram_character", "instagram_meme"]
    return _PLATFORM_IMAGE_PROMPT[keys[index % len(keys)]]


def _generate_xbanner(store: dict, copy: str, index: int) -> str:
    """X배너를 상단(가게 자체 소개)/하단(가게 정보+혜택 강조) 두 장으로 나눠
    생성한 뒤 세로로 이어붙여 base64 PNG 하나로 반환한다. 할인·이벤트
    문장은 파이썬에서 미리 분리해 하단에만 넣고, 카피 후보 인덱스에 따라
    사진/플랫 그래픽 포스터/타이포그래피 중심 스타일을 다르게 적용한다."""
    size = _PLATFORM_IMAGE_SIZE["xbanner"]
    top_key, bottom_key = _pick_xbanner_template(index)
    top_text, bottom_text = _split_benefit_clause(copy)

    top_prompt = _PLATFORM_IMAGE_PROMPT[top_key].format(
        store_type=store.get("type", "가게"), copy=top_text
    )
    top_b64 = generate_image(top_prompt, size=size)
    top_img = Image.open(io.BytesIO(base64.b64decode(top_b64)))

    provided_info = f'상호 "{store.get("name")}", 주소 "{store.get("address")}"'
    if bottom_text:
        benefit_clause = (
            "다음 혜택 정보를 조건까지 포함해 하나의 배지·스티커 안에 통째로 "
            f'표시한다: "{bottom_text}" 이 배지를 화면에서 가장 크고 눈에 '
            "띄게 강조해서 배치한다. "
            "문구를 다른 표현으로 바꾸거나 요약하지 않고 주어진 그대로 "
            "표시한다 — 특히 '무료'·'할인' 같은 단어만 따로 떼어내 별도의 "
            "거대한 문구로 만들지 않는다. 조건 없이 혜택 단어만 단독으로 "
            "화면에 크게 표시하지 않는다."
        )
    else:
        benefit_clause = "혜택을 강조하는 별도 텍스트는 넣지 않는다."
    bottom_prompt = _PLATFORM_IMAGE_PROMPT[bottom_key].format(
        store_name=store.get("name"),
        provided_info=provided_info,
        benefit_clause=benefit_clause,
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
                image_b64 = _generate_xbanner(store, c["copy"], i)
                top_key, _ = _pick_xbanner_template(i)
                top_text, bottom_text = _split_benefit_clause(c["copy"])
                bottom_desc = (
                    f'하단에는 상호·주소와 혜택 강조 문구("{bottom_text}")가 '
                    "표기된다."
                    if bottom_text
                    else "하단에는 상호·주소가 표기된다."
                )
                prompt_record = (
                    _PLATFORM_IMAGE_PROMPT[top_key].format(
                        store_type=store.get("type", "가게"), copy=top_text
                    )
                    + " "
                    + bottom_desc
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
            captions_en.append(_english_caption(store.get("type", "가게"), c["copy"]))
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
