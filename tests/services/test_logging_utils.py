from dataclasses import dataclass

import pytest
from pydantic import BaseModel, Field

from backend.logging_utils import (
    MAX_FIELD_CHARS,
    MAX_PAYLOAD_CHARS,
    payload_for_log,
    redact_payload,
)


@pytest.mark.parametrize(
    "key",
    [
        "api_key",
        "OPENAI_API_KEY",
        "openai_api_key",
        "NAVER_MAPS_API_KEY",
        "HF_TOKEN",
        "access_token",
        "refresh_token",
        "session_secret_key",
        "Authorization",
        "password",
        "password_hash",
        "image_b64",
        "image_url",
        "thumbnail_b64",
        "service_credential",
    ],
)
def test_secret_keys_are_redacted(key):
    out = redact_payload({key: "sk-super-secret-1234567890"})

    assert "sk-super-secret" not in str(out[key])


@pytest.mark.parametrize(
    "key", ["tokens_used", "proposals", "copy", "title", "generation_id"]
)
def test_normal_fields_are_not_redacted(key):
    assert redact_payload({key: "값1234"})[key] == "값1234"


def test_pydantic_model_is_flattened_before_redaction():
    class Proposal(BaseModel):
        copy_text: str = Field(alias="copy")
        image_b64: str

    class Result(BaseModel):
        status: str
        proposals: list[Proposal]
        tokens_used: int

    image = "a" * (200 * 1024)
    result = Result(
        status="ok",
        proposals=[
            Proposal.model_validate({"copy": f"문구 {i}", "image_b64": image})
            for i in range(3)
        ],
        tokens_used=1520,
    )

    text = payload_for_log(result)

    assert image[:40] not in text
    assert "tokens_used" in text
    assert len(text) < MAX_PAYLOAD_CHARS


@dataclass
class DataclassPayload:
    status: str
    session_secret_key: str


def test_dataclass_is_flattened_before_redaction():
    out = redact_payload(DataclassPayload(status="ok", session_secret_key="secret"))

    assert out == {
        "status": "ok",
        "session_secret_key": "<session_secret_key omitted, len=6>",
    }


def test_model_dump_failure_does_not_break_logging():
    class Weird:
        def model_dump(self, **_kwargs):
            raise RuntimeError("boom")

    assert isinstance(payload_for_log({"obj": Weird()}), str)


def test_long_string_is_truncated_with_original_length():
    out = redact_payload({"copy": "가" * (MAX_FIELD_CHARS + 500)})["copy"]

    assert out.endswith(f"(total {MAX_FIELD_CHARS + 500} chars)")


def test_long_list_is_capped():
    out = redact_payload({"items": list(range(20))})["items"]

    assert out[-1] == "<...15 items omitted>"


def test_deep_nesting_is_cut():
    deep = {"a": {"b": {"c": {"d": {"e": {"f": "값"}}}}}}

    assert "<...>" in str(redact_payload(deep))


def test_payload_for_log_never_exceeds_limit():
    out = payload_for_log({"x": ["가" * 200] * 100})

    assert len(out) <= MAX_PAYLOAD_CHARS + len("...(truncated)")
