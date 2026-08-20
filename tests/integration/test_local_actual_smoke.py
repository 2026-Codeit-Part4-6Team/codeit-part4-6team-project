from scripts.local_actual_smoke import missing_required_environment


def test_actual_smoke_requires_openai_api_key() -> None:
    assert missing_required_environment({}) == ["OPENAI_API_KEY"]


def test_actual_smoke_accepts_openai_api_key() -> None:
    assert missing_required_environment({"OPENAI_API_KEY": "test-key"}) == []


def test_actual_env_example_documents_local_runtime() -> None:
    from pathlib import Path

    text = Path('.env.actual.example').read_text(encoding='utf-8')
    assert 'CHATBOT_MODE=actual' in text
    assert 'OPENAI_API_KEY=' in text
    assert 'OPENAI_MODEL=gpt-4o-mini' in text
