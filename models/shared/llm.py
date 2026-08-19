"""
models/shared/llm.py 
— 두 챗봇 공통 OpenAI 호출 래퍼 (관리: 전민재 PM)

OpenAI Chat Completion 공통 래퍼.

컨설턴트 구현본(D-035)을 토대로, 기본 챗봇이 필요로 한 두 기능을 합쳤다.
  · (text, tokens) 반환 — 계약상 tokens_used가 두 챗봇 모두 필수 필드다
  · json_mode — response_format으로 JSON을 강제해 파싱 실패를 줄인다
여기에 D-049(요청 데드라인)를 추가했다. 재시도 백오프(최대 14초)가
서비스 타임아웃 60초를 잠식하지 않도록, 남은 예산이 다음 대기시간보다
짧으면 재시도를 포기하고 즉시 예외를 올린다.

RateLimitError(429)만 재시도 대상이며 그 외 예외는 즉시 전파한다.
SDK 자체 재시도(max_retries)는 0으로 꺼서 수동 백오프와 중첩되지 않게 한다.
"""

import logging
import time

import openai
from openai import OpenAI

from models.shared.config import (
    LLM_BACKOFF_SECONDS,
    LLM_DEADLINE_SECONDS,
    LLM_MAX_RETRIES,
    LLM_TEMPERATURE,
    LLM_TIMEOUT_SECONDS,
    OPENAI_BASE_URL,
    OPENAI_MODEL,
)

logger = logging.getLogger(__name__)

_client: OpenAI | None = None
_total_tokens: dict[str, int] = {}


def _get_client() -> OpenAI:
    """클라이언트를 1회만 생성해 재사용한다(커넥션 재사용·소켓 누수 방지)."""
    global _client
    if _client is None:
        _client = OpenAI(
            max_retries=0,
            timeout=LLM_TIMEOUT_SECONDS,
            base_url=OPENAI_BASE_URL,
        )
    return _client


def reset_client() -> None:
    """테스트에서 캐시된 클라이언트를 비운다."""
    global _client
    _client = None

def reset_total_tokens() -> None:
    """테스트에서 누적 토큰 카운터를 비운다."""
    _total_tokens.clear()


def get_total_tokens(model: str | None = None) -> int:
    """프로세스 시작 이후 누적 토큰 수 — $30 예산 모니터링·평가 스크립트용.

    model 을 지정하면 그 모델만, 생략하면 전체 합계를 반환한다(D-257).
    생성 모델과 Judge 모델의 소비량을 나눠 보기 위해 모델별로 집계한다.
    집계에 없는 모델을 조회해도 KeyError 가 아니라 0 을 반환한다.
    """
    if model is None:
        return sum(_total_tokens.values())
    return _total_tokens.get(model, 0)

def call_llm(
    system: str,
    user: str,
    *,
    json_mode: bool = False,
    deadline: float | None = None,
    model: str | None = None,          # ← None 이면 OPENAI_MODEL
) -> tuple[str, int]:
    """OpenAI를 호출해 (응답 텍스트, 사용 토큰 수)를 반환한다.
    model 을 지정하면 그 모델로 호출한다 — LLM Judge 처럼 생성과 다른 모델을
    써야 하는 경우에만 쓴다(D-251). 기본값 None 은 OPENAI_MODEL 이므로
    기존 호출부(노드 전부)는 한 줄도 바뀌지 않는다.

    Args:
        system: 시스템 프롬프트.
        user: 사용자 프롬프트.
        json_mode: True면 JSON 객체 응답을 강제한다.
        deadline: time.monotonic() 기준 절대 마감 시각.
            생략하면 호출 시점부터 LLM_DEADLINE_SECONDS를 예산으로 쓴다.

    Raises:
        openai.RateLimitError: 재시도 상한 도달 또는 남은 예산 부족.
        ValueError: 응답에 텍스트 content가 없을 때.
    """
    if deadline is None:
        deadline = time.monotonic() + LLM_DEADLINE_SECONDS

    # ★ 한 번만 해석해서 호출·집계 양쪽에 같은 값을 쓴다.
    #   raw model 을 집계 키로 쓰면 생략 시 None 이 키가 되어 집계가 깨진다(D-264).
    resolved_model = model or OPENAI_MODEL

    kwargs = {"response_format": {"type": "json_object"}} if json_mode else {}
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]

    for attempt in range(LLM_MAX_RETRIES + 1):
        try:
            response = _get_client().chat.completions.create(
                model=resolved_model,
                temperature=LLM_TEMPERATURE,
                messages=messages,
                **kwargs,
            )
            content = response.choices[0].message.content
            if content is None:
                raise ValueError("OpenAI 응답에 텍스트 content가 없습니다.")

            tokens = response.usage.total_tokens if response.usage else 0
            # dict 는 없는 키에 += 가 KeyError 다 — get(k, 0) 으로 초기값을 준다.
            _total_tokens[resolved_model] = _total_tokens.get(resolved_model, 0) + tokens
            return content, tokens

        except openai.RateLimitError:
            if attempt >= LLM_MAX_RETRIES:
                logger.warning("429 재시도 상한(%d회) 도달", LLM_MAX_RETRIES)
                raise
            # 상수를 늘려도 IndexError가 나지 않도록 마지막 값을 재사용한다
            wait = LLM_BACKOFF_SECONDS[min(attempt, len(LLM_BACKOFF_SECONDS) - 1)]
            remaining = deadline - time.monotonic()
            if remaining <= wait:
                logger.warning(
                    "429 재시도 포기 — 남은 예산 %.1f초 < 대기 %d초", remaining, wait
                )
                raise
            logger.info("429 수신 — %d초 후 재시도(%d/%d)", wait, attempt + 1, LLM_MAX_RETRIES)
            time.sleep(wait)

    raise RuntimeError("call_llm: 재시도 루프가 값을 반환하지 못했습니다.")  # 도달 불가 방어