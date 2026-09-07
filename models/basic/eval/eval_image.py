"""골든 데이터셋 area=basic 문항으로 이미지 생성 결과를 평가한다.

B- 문항 중 지정된 개수(기본 20개)를 골라 카피 생성 → 이미지 생성 → CLIP
Score(정합성)를 산출한다. 멀티모달 LLM-Judge는 비용이 더 커서 별도 단계로
남겨둔다.

실행: uv run python -m models.basic.eval.eval_image --dataset shared_data/golden_dataset.json
--banner-limit 5 --instagram-limit 10 --exclude B-012,B-040,B-057

models/shared/eval_fixtures.py 파일 도착 후 실행 가능하다.
"""

import argparse
import base64
import io
import json
import sys
import time
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

from openai import OpenAI
from PIL import Image

from models.basic.clients.image_client import IMAGE_MODEL, generate_image
from models.basic.nodes.channel import channel_node
from models.basic.nodes.copy_gen import copy_gen_node
from models.basic.nodes.image_gen import (
    _DEFAULT_PLATFORM,
    _PLATFORM_IMAGE_PROMPT,
    _english_caption,
    _extract_business_details,
    _generate_xbanner,
    _pick_instagram_template,
    _pick_xbanner_template,
    _split_benefit_clause,
)
from models.basic.nodes.image_review import _clip_score
from models.basic.nodes.market_for_copy import market_for_copy_node
from models.basic.nodes.trend_for_copy import trend_for_copy_node
from models.shared.config import OPENAI_MODEL
from models.shared.eval_fixtures import build_model_request

DATASET_VERSION = "v1.2"
_OUTPUT_DIR = Path(__file__).parent / "image_samples"

_vision_client: OpenAI | None = None


def _get_vision_client() -> OpenAI:
    global _vision_client
    if _vision_client is None:
        _vision_client = OpenAI()
    return _vision_client


_IMAGE_RUBRIC_CRITERIA = {
    "instagram": {
        "브랜드_제품_정합성": "이미지가 카피·업종과 실제로 일치하는 제품/메뉴를 보여주는가(엉뚱한 음료·음식이 아닌가)",
        "인스타_피드_적합성": "정사각형/세로형 구도에 주요 피사체가 중앙에 잘 배치되고, 인물·사물 왜곡 같은 생성 아티팩트가 없는가",
        "분위기_톤_일치": "카피의 톤(발랄함·차분함 등)과 이미지 분위기가 서로 맞는가",
        "텍스트_정확도": "이미지 안에 표시된 한글 텍스트가 카피 원문과 정확히 일치하는가(깨지거나 다른 글자면 낮은 점수)",
    },
    "xbanner": {
        "브랜드_제품_정합성": "이미지가 카피·업종과 실제로 일치하는 제품/메뉴를 보여주는가(엉뚱한 음료·음식이 아닌가)",
        "배너_가독성": "상단 카피 문구가 정확한 철자로 읽기 쉽게 표시되고, 하단 가게 정보와 시각적으로 잘 구분되는가",
        "분위기_톤_일치": "카피의 톤(발랄함·차분함 등)과 이미지 분위기가 서로 맞는가",
        "텍스트_정확도": "이미지 안에 표시된 한글 텍스트가 카피 원문과 정확히 일치하는가(깨지거나 다른 글자면 낮은 점수)",
    },
}


def judge_image_rubric(
    store: dict, copy: str, image: Image.Image, platform: str
) -> tuple[dict, dict]:
    """비전 모델(gpt-4o-mini)로 이미지 rubric 4항목(텍스트_정확도 포함)을
    1~5점으로 채점하고, 같은 호출에서 표시광고법 위반 소지가 있는 문구가
    이미지 안에 그대로 노출됐는지도 함께 판정한다(카피는 check_regulation을
    타지만 이미지 안 문구는 안 타므로 별도 확인이 필요하다)."""
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    image_b64 = base64.b64encode(buf.getvalue()).decode()

    criteria = _IMAGE_RUBRIC_CRITERIA.get(
        platform, _IMAGE_RUBRIC_CRITERIA[_DEFAULT_PLATFORM]
    )
    criteria_text = "\n".join(f"- {k}: {v}" for k, v in criteria.items())
    rubric_format = "{" + ", ".join(f'"{k}": 0' for k in criteria) + "}"

    prompt = (
        f"## 가게 정보\n업종: {store.get('type', '')}\n\n"
        f"## 광고 카피\n{copy}\n\n"
        "아래 평가 기준마다 1~5점을 매겨라.\n"
        f"{criteria_text}\n\n"
        "추가로, 이미지 안에 실제로 표시된 텍스트 중 조건 없는 할인·무료·"
        "증정 주장(예: 조건 설명 없이 '무료!'만 크게 강조)이나 '완벽한', "
        "'걱정 없이' 같은 절대적·기만적 표현이 있는지 확인하라.\n\n"
        "JSON으로만 답한다. 형식: "
        f'{{"rubric": {rubric_format}, "regulation_flagged": false, '
        '"regulation_reason": null}}'
    )

    response = _get_vision_client().chat.completions.create(
        model=OPENAI_MODEL,
        temperature=0.0,
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "system",
                "content": "너는 광고 이미지 품질과 표시광고법 준수 여부를 함께 심사하는 심사위원이다.",
            },
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{image_b64}"},
                    },
                ],
            },
        ],
    )
    parsed = json.loads(response.choices[0].message.content)
    rubric = parsed.get("rubric", {})
    regulation = {
        "flagged": parsed.get("regulation_flagged", False),
        "reason": parsed.get("regulation_reason"),
    }
    return rubric, regulation


def moderation_check(image: Image.Image) -> dict:
    """OpenAI Moderation API로 이미지의 콘텐츠 안전성을 검사한다(무료 API).
    flagged가 True면 부적절한 콘텐츠로 판정된 것이다."""
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    image_b64 = base64.b64encode(buf.getvalue()).decode()

    response = _get_vision_client().moderations.create(
        model="omni-moderation-latest",
        input=[
            {
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{image_b64}"},
            }
        ],
    )
    result = response.results[0]
    flagged_categories = [
        category for category, value in result.categories.model_dump().items() if value
    ]
    return {"flagged": result.flagged, "categories": flagged_categories}


_MARKET_FIXTURE = {
    "total_count": 6691,
    "same_industry_count": 177,
    "nearest_distance_m": 80,
}

_TREND_FIXTURE = {
    "keyword": "카페",
    "direction": "유지",
    "related": [],
}


def _fake_get_market(lat, lng, radius=500, industry=None):
    return _MARKET_FIXTURE


def _fake_get_trend(keyword, industry=None):
    return {**_TREND_FIXTURE, "keyword": keyword}


def _avg_rgb(image: Image.Image) -> tuple[float, float, float]:
    rgb_image = image.convert("RGB")
    pixels = list(rgb_image.getdata())
    n = len(pixels)
    r = sum(p[0] for p in pixels) / n
    g = sum(p[1] for p in pixels) / n
    b = sum(p[2] for p in pixels) / n
    return (r, g, b)


def _xbanner_tone_similarity(image: Image.Image) -> float:
    """xbanner 합성 이미지를 절반으로 나눠 상단·하단의 평균 색상 거리를
    정규화된 유사도(0~1, 1이 완전 일치)로 반환한다. API 호출 없이 PIL만
    쓴다."""
    w, h = image.size
    top_avg = _avg_rgb(image.crop((0, 0, w, h // 2)))
    bottom_avg = _avg_rgb(image.crop((0, h // 2, w, h)))
    dist = sum((a - b) ** 2 for a, b in zip(top_avg, bottom_avg)) ** 0.5
    max_dist = (255**2 * 3) ** 0.5
    return round(1 - dist / max_dist, 3)


def _build_context(request: dict) -> dict:
    """copy_gen이 참고할 market/trend 컨텍스트를 eval_generation.py와 동일한
    고정 fixture로 채운다(§1.4 재현성 원칙, 외부 API 미호출). question_analysis를
    안 거치므로 keyword는 질문 원문으로 대체한다."""
    state = {
        "store": request["store"],
        "keyword": request["question"],
        "context": {},
    }
    with (
        patch(
            "models.basic.nodes.market_for_copy.get_market",
            side_effect=_fake_get_market,
        ),
        patch(
            "models.basic.nodes.trend_for_copy.get_trend", side_effect=_fake_get_trend
        ),
    ):
        state["context"] = {
            **state["context"],
            **market_for_copy_node(state).get("context", {}),
        }
        state["context"] = {
            **state["context"],
            **trend_for_copy_node(state).get("context", {}),
        }
    return state["context"]


# 골든 데이터셋 기반 평가


def _next_run_dir(base_dir: Path) -> Path:
    """같은 날 여러 번 실행해도 이전 결과를 덮어쓰지 않도록, base_dir 아래에
    날짜(-번호) 이름의 새 하위 디렉터리를 만들어 반환한다."""
    today = datetime.now(UTC).date()
    run_dir = base_dir / str(today)
    n = 2
    while run_dir.exists():
        run_dir = base_dir / f"{today}-{n}"
        n += 1
    return run_dir


def _pick_copies(copy_candidates: list[dict]) -> list[str]:
    return [c["copy"] for c in copy_candidates if c.get("copy")]


def _evaluate_item(item: dict, run_dir: Path) -> dict:
    request = build_model_request(item)
    store = request["store"]
    context = _build_context(request)
    platform = channel_node({"platform": request.get("platform")})["platform"]

    copy_result = copy_gen_node(
        {
            "question": request["question"],
            "platform": platform,
            "store": store,
            "extra": request.get("extra") or {},
            "context": context,
        }
    )
    copies = _pick_copies(copy_result.get("copy_candidates", []))
    if not copies:
        return {"id": item["id"], "passed": False, "reason": "copy_generation_failed"}
    business_details = (
        _extract_business_details(request["question"])
        if platform == "xbanner"
        else None
    )

    image_evals = []
    total_latency = 0.0
    for i, copy in enumerate(copies):
        start = time.monotonic()
        if platform == "xbanner":
            image_b64 = _generate_xbanner(store, copy, i, business_details)
            top_key, _ = _pick_xbanner_template(i)
            top_text, _ = _split_benefit_clause(copy, store.get("type", "가게"))
            image_prompt = _PLATFORM_IMAGE_PROMPT[top_key].format(
                store_type=store.get("type", "가게"), copy=top_text
            )
        else:
            template = _pick_instagram_template(store, i)
            image_prompt = template.format(
                store_type=store.get("type", "가게"), copy=copy
            )
            image_b64 = generate_image(image_prompt)
        total_latency += time.monotonic() - start
        image = Image.open(io.BytesIO(base64.b64decode(image_b64)))

        caption = _english_caption(store.get("type", "store"), copy)
        clip = _clip_score(image, caption or image_prompt)

        image_rubric, regulation_check = judge_image_rubric(
            store, copy, image, platform
        )
        moderation = moderation_check(image)
        tone_similarity = (
            _xbanner_tone_similarity(image) if platform == "xbanner" else None
        )

        image_path = run_dir / f"{item['id']}_{i}.png"
        image.save(image_path)

        image_evals.append(
            {
                "copy": copy,
                "image_prompt": image_prompt,
                "caption_en": caption,
                "clip_score": clip,
                "image_rubric": image_rubric,
                "regulation_check": regulation_check,
                "moderation": moderation,
                "tone_similarity": tone_similarity,
                "latency_s": round(time.monotonic() - start, 2),
                "image_path": str(image_path),
            }
        )

    return {
        "id": item["id"],
        "passed": True,
        "platform": platform,
        "image_count": len(image_evals),
        "latency_s": round(total_latency, 2),
        "images": image_evals,
    }


def run(
    dataset_path: Path,
    limit: int,
    banner_limit: int | None = None,
    instagram_limit: int | None = None,
    exclude: list[str] | None = None,
) -> dict:
    all_items = json.loads(dataset_path.read_text(encoding="utf-8"))
    basic_items = [i for i in all_items if i["area"] == "basic"]
    if exclude:
        basic_items = [i for i in basic_items if i["id"] not in exclude]

    if banner_limit is not None or instagram_limit is not None:
        banner_items = [
            i for i in basic_items if i["input"].get("platform") == "banner"
        ][: banner_limit or 0]
        instagram_items = [
            i for i in basic_items if i["input"].get("platform") == "instagram"
        ][: instagram_limit or 0]
        items = banner_items + instagram_items
    else:
        items = basic_items[:limit]

    if not items:
        print("basic 문항이 없습니다.", file=sys.stderr)
        sys.exit(1)

    run_dir = _next_run_dir(_OUTPUT_DIR)
    run_dir.mkdir(parents=True, exist_ok=True)

    results = []
    for item in items:
        print(f"처리 중: {item['id']}...")
        result = _evaluate_item(item, run_dir)
        results.append(result)
        time.sleep(1)  # 직렬 실행 + 요청 간 sleep (§10.4·§10.5)

    processed = len(results)
    if processed != len(items):
        print(f"basic {len(items)}문항 중 {processed}건 처리 — 불일치", file=sys.stderr)
        sys.exit(1)
    print(f"basic {len(items)}문항 중 {processed}건 처리")

    passed = [r for r in results if r["passed"]]
    all_image_evals = [img for r in passed for img in r["images"]]

    clip_scores = [img["clip_score"] for img in all_image_evals]

    rubric_by_criterion = defaultdict(list)
    for img in all_image_evals:
        for k, v in (img.get("image_rubric") or {}).items():
            rubric_by_criterion[k].append(v)
    image_rubric_avg = {
        k: round(sum(v) / len(v), 2) for k, v in rubric_by_criterion.items()
    }

    moderation_flagged = [img["moderation"]["flagged"] for img in all_image_evals]
    moderation_flagged_rate = (
        round(sum(moderation_flagged) / len(moderation_flagged), 3)
        if moderation_flagged
        else None
    )

    regulation_flagged = [img["regulation_check"]["flagged"] for img in all_image_evals]
    regulation_flagged_rate = (
        round(sum(regulation_flagged) / len(regulation_flagged), 3)
        if regulation_flagged
        else None
    )

    per_image_latencies = [img["latency_s"] for img in all_image_evals]
    avg_latency_per_image_s = (
        round(sum(per_image_latencies) / len(per_image_latencies), 2)
        if per_image_latencies
        else None
    )

    tone_similarities = [
        img["tone_similarity"]
        for img in all_image_evals
        if img.get("tone_similarity") is not None
    ]
    xbanner_tone_similarity_avg = (
        round(sum(tone_similarities) / len(tone_similarities), 3)
        if tone_similarities
        else None
    )

    report = {
        "run_at": datetime.now(UTC).isoformat(),
        "area": "basic_image",
        "models": {"copy": OPENAI_MODEL, "image": IMAGE_MODEL},
        "dataset_version": DATASET_VERSION,
        "item_count": processed,
        "metrics": {
            "success_rate": round(len(passed) / processed, 3) if processed else 0,
            "image_rubric_avg": image_rubric_avg,
            "clip_score_avg": (
                round(sum(clip_scores) / len(clip_scores), 4) if clip_scores else None
            ),
            "moderation_flagged_rate": moderation_flagged_rate,
            "regulation_flagged_rate": regulation_flagged_rate,
            "avg_latency_per_image_s": avg_latency_per_image_s,
            "xbanner_tone_similarity_avg": xbanner_tone_similarity_avg,
        },
        "items": results,
    }

    out_dir = Path("models/basic/eval/reports")
    out_dir.mkdir(parents=True, exist_ok=True)
    today = datetime.now(UTC).date()
    out_path = out_dir / f"image_{today}.json"
    n = 2
    while out_path.exists():
        out_path = out_dir / f"image_{today}-{n}.json"
        n += 1
    out_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"결과 저장: {out_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--banner-limit", type=int, default=None, help="banner 문항 수")
    parser.add_argument(
        "--instagram-limit", type=int, default=None, help="instagram 문항 수"
    )
    parser.add_argument(
        "--exclude",
        type=str,
        default="",
        help="제외할 문항 ID, 콤마로 구분 (예: B-012)",
    )
    args = parser.parse_args()
    exclude = [x.strip() for x in args.exclude.split(",") if x.strip()]
    run(args.dataset, args.limit, args.banner_limit, args.instagram_limit, exclude)
