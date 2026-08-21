from pathlib import Path

ROOT = Path(__file__).parents[2]


def test_compose_passes_chatbot_mode_to_backend():
    compose = (ROOT / "compose.yaml").read_text()

    assert "CHATBOT_MODE: ${CHATBOT_MODE:-mock}" in compose


def test_env_example_documents_chatbot_mode():
    env_example = (ROOT / ".env.example").read_text(encoding="utf-8")

    assert "CHATBOT_MODE=mock" in env_example


def test_backend_image_contains_actual_model_code_and_dependencies():
    dockerfile = (ROOT / "backend" / "Dockerfile").read_text()

    assert "--only-group backend" in dockerfile
    assert "--only-group model-consult" in dockerfile
    assert "--only-group basic" in dockerfile
    assert "COPY models ./models" in dockerfile


def test_compose_passes_actual_model_environment_to_backend():
    compose = (ROOT / "compose.yaml").read_text()

    required_environment = [
        "OPENAI_API_KEY: ${OPENAI_API_KEY:-}",
        "OPENAI_MODEL: ${OPENAI_MODEL:-gpt-4o-mini}",
        "OPENAI_BASE_URL: ${OPENAI_BASE_URL:-https://api.openai.com/v1}",
        "LLM_TEMPERATURE: ${LLM_TEMPERATURE:-0.3}",
        "MARKET_API_KEY: ${MARKET_API_KEY:-}",
        "NAVER_CLIENT_ID: ${NAVER_CLIENT_ID:-}",
        "NAVER_CLIENT_SECRET: ${NAVER_CLIENT_SECRET:-}",
        "NAVER_AD_API_KEY: ${NAVER_AD_API_KEY:-}",
        "NAVER_AD_SECRET_KEY: ${NAVER_AD_SECRET_KEY:-}",
        "NAVER_AD_CUSTOMER_ID: ${NAVER_AD_CUSTOMER_ID:-}",
    ]

    for entry in required_environment:
        assert entry in compose
