# model_consult/llm.py — OpenAI 호출 래퍼(+429 지수 백오프)
import time

import openai
from openai import OpenAI

from model_consult.config import (
    LLM_BACKOFF_SECONDS,
    LLM_MAX_RETRIES,
    LLM_TEMPERATURE,
    OPENAI_MODEL,
)


def call_llm(system_prompt: str, user_prompt: str) -> str:
    """OpenAI Chat Completion을 호출해 응답 텍스트를 반환한다.

    RateLimitError(429)만 재시도 대상이며, 최초 호출 포함 최대 4회 시도한다
    (재시도 3회, 대기 2→4→8초). 마지막 시도까지 실패하면 예외를 그대로 올린다.
    RateLimitError가 아닌 예외는 즉시 전파한다(재시도 없음).
    SDK 자체 재시도(max_retries)는 0으로 꺼서 이 함수의 수동 백오프와 중첩되지 않게 한다.
    응답 content가 None이면(OpenAI SDK 타입상 Optional) ValueError를 발생시켜
    -> str 계약을 지킨다 — 그대로 반환하면 호출하는 쪽의 json.loads() 등에서
    더 알아보기 어려운 예외로 이어진다.
    """
    client = OpenAI(max_retries=0)
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    for attempt in range(LLM_MAX_RETRIES + 1):
        try:
            response = client.chat.completions.create(
                model=OPENAI_MODEL,
                temperature=LLM_TEMPERATURE,
                messages=messages,
            )
            content = response.choices[0].message.content
            if content is None:
                raise ValueError("OpenAI 응답에 텍스트 content가 없습니다.")
            return content
        except openai.RateLimitError:
            if attempt == LLM_MAX_RETRIES:
                raise
            time.sleep(LLM_BACKOFF_SECONDS[attempt])
