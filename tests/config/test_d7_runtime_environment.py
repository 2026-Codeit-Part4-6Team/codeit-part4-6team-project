from pathlib import Path

from backend.config import load_settings

ROOT = Path(__file__).parents[2]


def test_d7_timeout_and_executor_defaults_are_documented(monkeypatch):
    for name in (
        "MODEL_REQUEST_TIMEOUT_SECONDS",
        "MODEL_THREAD_POOL_WORKERS",
        "STALE_RECOVERY_SECONDS",
        "CHATBOT_MODE",
    ):
        monkeypatch.delenv(name, raising=False)

    settings = load_settings()

    assert settings.model_request_timeout_seconds == 180
    assert settings.model_thread_pool_workers == 2
    assert settings.stale_recovery_seconds == 120
    assert settings.chatbot_mode == "mock"


def test_compose_passes_runtime_credentials_and_timeout():
    compose = (ROOT / "compose.yaml").read_text(encoding="utf-8")
    env_example = (ROOT / ".env.example").read_text(encoding="utf-8")

    for entry in (
        "MODEL_REQUEST_TIMEOUT_SECONDS: ${MODEL_REQUEST_TIMEOUT_SECONDS:-180}",
        "CHATBOT_MODE: ${CHATBOT_MODE:-mock}",
    ):
        assert entry in compose

    for entry in (
        "MODEL_REQUEST_TIMEOUT_SECONDS=180",
        "MODEL_THREAD_POOL_WORKERS=2",
        "STALE_RECOVERY_SECONDS=120",
        "CHATBOT_MODE=mock",
        "OPENAI_API_KEY=",
        "HF_TOKEN=",
    ):
        assert entry in env_example
