from pydantic import BaseModel

from backend.logging_utils import payload_for_log, redact_payload


def test_redact_payload_masks_secret_suffixes_without_matching_usage_counters():
    payload = {
        "OPENAI_API_KEY": "openai-secret",
        "NAVER_MAPS_API_KEY": "naver-secret",
        "HF_TOKEN": "hf-secret",
        "session_secret_key": "session-secret",
        "tokens_used": 42,
    }

    redacted = redact_payload(payload)

    assert redacted["OPENAI_API_KEY"] == "<OPENAI_API_KEY omitted, len=13>"
    assert redacted["NAVER_MAPS_API_KEY"] == "<NAVER_MAPS_API_KEY omitted, len=12>"
    assert redacted["HF_TOKEN"] == "<HF_TOKEN omitted, len=9>"
    assert redacted["session_secret_key"] == "<session_secret_key omitted, len=14>"
    assert redacted["tokens_used"] == 42


def test_payload_for_log_dumps_pydantic_models_before_redacting():
    class ModelResultPayload(BaseModel):
        status: str
        tokens_used: int
        image_b64: str

    payload = ModelResultPayload(
        status="ok",
        tokens_used=123,
        image_b64="a" * 2_000,
    )

    logged = payload_for_log(payload)

    assert "status" in logged
    assert "tokens_used" in logged
    assert "123" in logged
    assert "a" * 100 not in logged
    assert "image_b64 omitted" in logged
