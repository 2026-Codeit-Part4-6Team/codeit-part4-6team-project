from scripts.local_actual_smoke import missing_required_environment


def test_actual_smoke_requires_openai_api_key() -> None:
    assert missing_required_environment({}) == ["OPENAI_API_KEY"]


def test_actual_smoke_accepts_openai_api_key() -> None:
    assert missing_required_environment({"OPENAI_API_KEY": "test-key"}) == []


def test_env_example_documents_actual_model_runtime() -> None:
    from pathlib import Path

    text = Path('.env.example').read_text(encoding='utf-8')
    assert 'CHATBOT_MODE=mock' in text
    assert 'OPENAI_API_KEY=' in text
    assert 'OPENAI_MODEL=' in text


def test_local_actual_test_guide_uses_project_env_file() -> None:
    from pathlib import Path

    guide = Path("docs/d7_local_actual_test.md").read_text(encoding="utf-8")
    legacy_env = ".env" + ".actual"
    assert legacy_env not in guide
    assert "--env-file .env" in guide
