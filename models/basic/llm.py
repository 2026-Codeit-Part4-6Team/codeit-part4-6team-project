import time

import openai
from openai import OpenAI

MODEL_NAME = "gpt-4o-mini"
LLM_TEMPERATURE = 0.3
LLM_MAX_RETRIES = 3
LLM_BACKOFF_SECONDS = [2, 4, 8]


def call_llm(system: str, user: str, json_mode: bool = False) -> tuple[str, int]:
    """OpenAI Chat Completion을 호출해 (응답 텍스트, 사용 토큰 수)를 반환한다.

    RateLimitError(429)만 재시도 대상이며, 최초 호출 포함 최대 4회 시도한다
    (재시도 3회, 대기 2→4→8초). SDK 자체 재시도(max_retries)는 0으로 꺼서
    이 함수의 수동 백오프와 중첩되지 않게 한다.
    """
    client = OpenAI(max_retries=0)
    kwargs = {"response_format": {"type": "json_object"}} if json_mode else {}

    for attempt in range(LLM_MAX_RETRIES + 1):
        try:
            response = client.chat.completions.create(
                model=MODEL_NAME,
                temperature=LLM_TEMPERATURE,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                **kwargs,
            )
            content = response.choices[0].message.content
            if content is None:
                raise ValueError("OpenAI 응답에 텍스트 content가 없습니다.")
            tokens = response.usage.total_tokens if response.usage else 0
            return content, tokens
        except openai.RateLimitError:
            if attempt == LLM_MAX_RETRIES:
                raise
            time.sleep(LLM_BACKOFF_SECONDS[attempt])


def classify_llm_error(exc: Exception) -> str:
    """OpenAI 예외를 서비스 ErrorResult가 허용하는 reason
    (timeout/rate_limit/provider_error/unknown) 중 하나로 분류한다."""
    if isinstance(exc, openai.RateLimitError):
        return "rate_limit"
    if isinstance(exc, openai.APITimeoutError):
        return "timeout"
    if isinstance(exc, openai.APIError):
        return "provider_error"
    return "unknown"
