import tomllib
from pathlib import Path

ROOT = Path(__file__).parents[2]


def test_compose_passes_chatbot_mode_to_backend():
    compose = (ROOT / "compose.yaml").read_text(encoding="utf-8")

    assert "CHATBOT_MODE: ${CHATBOT_MODE:-mock}" in compose


def test_env_example_documents_chatbot_mode():
    env_example = (ROOT / ".env.example").read_text(encoding="utf-8")

    assert "CHATBOT_MODE=mock" in env_example


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
