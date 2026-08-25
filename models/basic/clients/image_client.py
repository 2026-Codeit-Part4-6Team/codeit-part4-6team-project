import time

import openai
from openai import OpenAI

from models.shared.config import LLM_BACKOFF_SECONDS, LLM_MAX_RETRIES

_client = None

IMAGE_MODEL = "gpt-image-2"
IMAGE_SIZE = "1024x1024"
IMAGE_QUALITY = "low"  # 팀 공용 $30 예산 고려 — 품질 필요하면 medium/high로 조정


def _get_client():
    global _client
    if _client is None:
        _client = OpenAI(max_retries=0)
    return _client


def generate_image(prompt: str, size: str = IMAGE_SIZE) -> str:
    """프롬프트를 받아 이미지를 생성하고 base64 인코딩된 이미지 문자열을 반환한다.

    OpenAI gpt-image-2를 사용한다. RateLimitError(429)만 재시도 대상이며,
    최초 호출 포함 최대 4회 시도한다. SDK 자체 재시도(max_retries)는 0으로
    꺼서 수동 백오프와 중첩되지 않게 한다.
    """
    client = _get_client()
    for attempt in range(LLM_MAX_RETRIES + 1):
        try:
            response = client.images.generate(
                model=IMAGE_MODEL,
                prompt=prompt,
                size=size,
                quality=IMAGE_QUALITY,
                n=1,
            )
            return response.data[0].b64_json
        except openai.RateLimitError:
            if attempt >= LLM_MAX_RETRIES:
                raise
            wait = LLM_BACKOFF_SECONDS[min(attempt, len(LLM_BACKOFF_SECONDS) - 1)]
            time.sleep(wait)

    raise RuntimeError("generate_image: 재시도 루프가 값을 반환하지 못했습니다.")