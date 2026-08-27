import tomllib
from pathlib import Path

from backend.config import load_settings

ROOT = Path(__file__).parents[2]


def test_d7_timeout_and_executor_defaults_are_documented(monkeypatch):
    for name in (
        "MODEL_REQUEST_TIMEOUT_SECONDS",
        "MODEL_THREAD_POOL_WORKERS",
        "STALE_RECOVERY_SECONDS",
        "CHATBOT_MODE",
        "MAX_APPROVED_IMAGE_BYTES",
    ):
        monkeypatch.delenv(name, raising=False)

    settings = load_settings()

    assert settings.model_request_timeout_seconds == 180
    assert settings.model_thread_pool_workers == 2
    assert settings.stale_recovery_seconds == 120
    assert settings.chatbot_mode == "mock"
    assert settings.max_approved_image_bytes == 5_242_880


def test_compose_passes_runtime_credentials_and_timeout():
    compose = (ROOT / "compose.yaml").read_text(encoding="utf-8")
    env_example = (ROOT / ".env.example").read_text(encoding="utf-8")

    for entry in (
        "MODEL_REQUEST_TIMEOUT_SECONDS: ${MODEL_REQUEST_TIMEOUT_SECONDS:-180}",
        "MODEL_THREAD_POOL_WORKERS: ${MODEL_THREAD_POOL_WORKERS:-2}",
        "STALE_RECOVERY_SECONDS: ${STALE_RECOVERY_SECONDS:-120}",
        "CHATBOT_MODE: ${CHATBOT_MODE:-mock}",
        "MAX_APPROVED_IMAGE_BYTES: ${MAX_APPROVED_IMAGE_BYTES:-5242880}",
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


def test_compose_passes_actual_model_environment_to_backend():
    compose = (ROOT / "compose.yaml").read_text(encoding="utf-8")

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


def test_d7_actual_timeout_defaults_to_verified_180_seconds():
    config = (ROOT / "backend" / "config.py").read_text(encoding="utf-8")
    compose = (ROOT / "compose.yaml").read_text(encoding="utf-8")
    env_example = (ROOT / ".env.example").read_text(encoding="utf-8")

    assert '"MODEL_REQUEST_TIMEOUT_SECONDS", 180, minimum=60' in config
    assert "MODEL_REQUEST_TIMEOUT_SECONDS: ${MODEL_REQUEST_TIMEOUT_SECONDS:-180}" in compose
    assert "MODEL_REQUEST_TIMEOUT_SECONDS=180" in env_example


def test_actual_runtime_isolated_pool_validation_and_hf_cache_are_explicit():
    compose = (ROOT / "compose.yaml").read_text(encoding="utf-8")
    deploy = (ROOT / "compose.deploy.yaml").read_text(encoding="utf-8")
    env_example = (ROOT / ".env.example").read_text(encoding="utf-8")

    for entry in (
        "MODEL_THREAD_POOL_WORKERS: ${MODEL_THREAD_POOL_WORKERS:-2}",
        "STALE_RECOVERY_SECONDS: ${STALE_RECOVERY_SECONDS:-120}",
        "VALIDATION_DYNAMIC_TOP_K: ${VALIDATION_DYNAMIC_TOP_K:-0}",
        "VALIDATION_TOP_K: ${VALIDATION_TOP_K:-3}",
        "VALIDATION_MAX_TOP_K: ${VALIDATION_MAX_TOP_K:-3}",
        "VALIDATION_RAG_ENABLED: ${VALIDATION_RAG_ENABLED:-1}",
        "VALIDATION_REQUIRE_LEGAL_KB: ${VALIDATION_REQUIRE_LEGAL_KB:-1}",
        "VALIDATION_MIN_KB_CHUNKS: ${VALIDATION_MIN_KB_CHUNKS:-30}",
        "HF_TOKEN: ${HF_TOKEN:-}",
        "HF_HOME: ${HF_HOME:-/app/.cache/huggingface}",
    ):
        assert entry in compose

    assert "start_period: 90s" in compose
    assert "start_period: 90s" in deploy
    assert "MODEL_THREAD_POOL_WORKERS=2" in env_example
    assert "STALE_RECOVERY_SECONDS=120" in env_example
    assert "HF_HOME=/app/.cache/huggingface" in env_example


def test_actual_model_boundary_smoke_is_documented_as_e2e_preflight():
    workflow_readme = (ROOT / ".github" / "workflows" / "README.md").read_text(
        encoding="utf-8"
    )

    assert "RUN_MODEL_BOUNDARY_SMOKE=1" in workflow_readme
    assert "E2E" in workflow_readme


def test_basic_dependency_group_contains_runtime_embedding_dependencies():
    config = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))

    project_dependencies = config["project"].get("dependencies", [])
    basic_dependencies = config["dependency-groups"]["basic"]

    assert not any(dep.startswith("sentence-transformers") for dep in project_dependencies)
    assert any(dep.startswith("openai") for dep in basic_dependencies)
    assert any(dep.startswith("transformers") for dep in basic_dependencies)


def test_backend_image_has_ci_and_actual_runtime_targets():
    dockerfile = (ROOT / "backend" / "Dockerfile").read_text(encoding="utf-8")

    assert "FROM base AS ci" in dockerfile
    assert "FROM base AS actual" in dockerfile
    assert dockerfile.count("--mount=type=cache,target=/root/.cache/uv") >= 2

    ci_section = dockerfile.split("FROM base AS ci", 1)[1].split("FROM base AS actual", 1)[0]
    actual_section = dockerfile.split("FROM base AS actual", 1)[1]

    assert "--only-group backend" in ci_section
    assert "--only-group basic" not in ci_section
    assert "--only-group model-consult" not in ci_section

    for group in ("backend", "model-consult", "basic"):
        assert f"--only-group {group}" in actual_section

    for runtime_copy in (
        "COPY models ./models",
        "COPY cache ./cache",
        "COPY validation ./validation",
        "COPY shared_data ./shared_data",
    ):
        assert runtime_copy in actual_section


def test_actual_runtime_copy_sources_exist_in_d7_branch():
    """Docker COPY 단계가 모델 PR merge 전에도 경로 누락으로 깨지지 않아야 한다."""
    for runtime_dir in ("models", "cache", "validation", "shared_data"):
        assert (ROOT / runtime_dir).is_dir(), (
            f"Actual runtime source directory missing: {runtime_dir}"
        )


def test_compose_and_pr_ci_use_actual_build_target():
    compose = (ROOT / "compose.yaml").read_text(encoding="utf-8")
    workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(
        encoding="utf-8"
    )

    assert "target: ${BACKEND_BUILD_TARGET:-actual}" in compose
    assert "BACKEND_BUILD_TARGET: actual" in workflow
    assert "CHATBOT_MODE: mock" in workflow
