from pathlib import Path


ROOT = Path(__file__).parents[2]


def test_compose_passes_chatbot_mode_to_backend():
    compose = (ROOT / "compose.yaml").read_text()

    assert "CHATBOT_MODE: ${CHATBOT_MODE:-mock}" in compose


def test_env_example_documents_chatbot_mode():
    env_example = (ROOT / ".env.example").read_text()

    assert "CHATBOT_MODE=mock" in env_example
