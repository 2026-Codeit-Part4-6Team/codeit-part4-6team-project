"""로그에 남길 payload의 민감값과 대용량 값을 축약합니다."""

MAX_FIELD_CHARS = 300
MAX_PAYLOAD_CHARS = 2_000
MAX_LIST_ITEMS = 5
MAX_DEPTH = 4

REDACT_KEYS = {
    "api_key",
    "authorization",
    "image_b64",
    "password",
    "password_hash",
}


def redact_payload(value: object, _depth: int = 0) -> object:
    """민감값을 제거하고 깊이·문자열·목록 크기를 제한한 사본을 반환합니다."""
    if _depth > MAX_DEPTH:
        return "<...>"

    if isinstance(value, dict):
        redacted: dict[object, object] = {}
        for key, item in value.items():
            if isinstance(key, str) and key.lower() in REDACT_KEYS:
                size = len(item) if isinstance(item, str) else "?"
                redacted[key] = f"<{key} omitted, len={size}>"
            else:
                redacted[key] = redact_payload(item, _depth + 1)
        return redacted

    if isinstance(value, list):
        shown = [redact_payload(item, _depth + 1) for item in value[:MAX_LIST_ITEMS]]
        if len(value) > MAX_LIST_ITEMS:
            shown.append(f"<...{len(value) - MAX_LIST_ITEMS} items omitted>")
        return shown

    if isinstance(value, str) and len(value) > MAX_FIELD_CHARS:
        return f"{value[:MAX_FIELD_CHARS]}...(total {len(value)} chars)"

    return value


def payload_for_log(value: object) -> str:
    """한 로그 레코드에 안전하게 포함할 수 있는 길이의 문자열을 반환합니다."""
    text = str(redact_payload(value))
    if len(text) <= MAX_PAYLOAD_CHARS:
        return text
    return f"{text[:MAX_PAYLOAD_CHARS]}...(truncated)"
