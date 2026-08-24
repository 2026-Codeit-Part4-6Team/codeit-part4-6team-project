import openai


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


def classify_image_error(exc: Exception) -> str:
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
