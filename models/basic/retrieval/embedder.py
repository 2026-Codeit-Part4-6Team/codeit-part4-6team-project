import time

import openai
from openai import OpenAI

from models.shared.config import LLM_BACKOFF_SECONDS, LLM_MAX_RETRIES

_client = None


def _get_client():
    global _client
    if _client is None:
        _client = OpenAI(max_retries=0)
    return _client


def embed(text: str) -> list[float]:
    """OpenAI 임베딩 모델(text-embedding-3-small)로 텍스트를 벡터로 변환한다.

    RateLimitError(429)만 재시도 대상이며, 최초 호출 포함 최대 4회 시도한다.
    SDK 자체 재시도(max_retries)는 0으로 꺼서 수동 백오프와 중첩되지 않게 한다.
    """
    client = _get_client()
    for attempt in range(LLM_MAX_RETRIES + 1):
        try:
            response = client.embeddings.create(
                model="text-embedding-3-small",
                input=text,
            )
            return response.data[0].embedding
        except openai.RateLimitError:
            if attempt >= LLM_MAX_RETRIES:
                raise
            wait = LLM_BACKOFF_SECONDS[min(attempt, len(LLM_BACKOFF_SECONDS) - 1)]
            time.sleep(wait)

    raise RuntimeError("embed: 재시도 루프가 값을 반환하지 못했습니다.")
