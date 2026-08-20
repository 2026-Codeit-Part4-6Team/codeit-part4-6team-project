from pathlib import Path


def test_openai_base_url_defaults_to_official_endpoint_when_unset_or_empty():
    compose = Path("compose.yaml").read_text(encoding="utf-8")

    assert (
        "OPENAI_BASE_URL: ${OPENAI_BASE_URL:-https://api.openai.com/v1}"
        in compose
    )
