from pathlib import Path


ROOT = Path(__file__).parents[2]


def test_demo_compose_enables_demo_environment_without_changing_public_ports() -> None:
    compose = (ROOT / "compose.demo.yaml").read_text(encoding="utf-8")

    assert "APP_ENV: ${APP_ENV:-demo}" in compose
    assert "DEMO_PAYMENT_ENABLED: ${DEMO_PAYMENT_ENABLED:-true}" in compose
    assert "DEMO_ACCOUNTS_ENABLED: ${DEMO_ACCOUNTS_ENABLED:-true}" in compose
    assert '"${BACKEND_BIND_ADDRESS:-127.0.0.1}:${BACKEND_PORT:-18000}:8000"' in compose
    assert '"${FRONTEND_BIND_ADDRESS:-0.0.0.0}:${FRONTEND_PORT:-8501}:8501"' in compose
    assert "start_period: 90s" in compose


def test_demo_workflow_is_manual_and_targets_demo_environment() -> None:
    workflow = (ROOT / ".github" / "workflows" / "deploy-demo.yml").read_text(
        encoding="utf-8"
    )

    assert "name: Deploy Demo (시연용 CD)" in workflow
    assert "workflow_dispatch:" in workflow
    assert "source_ref:" in workflow
    assert "confirm_deploy:" in workflow
    assert "environment: demo" in workflow
    assert "compose.demo.yaml" in workflow
    assert "DEMO_VM_DEPLOY_PATH" in workflow
    assert "DEMO_COMPOSE_PROJECT_NAME" in workflow
    assert "DEMO_PUBLIC_HEALTHCHECK_URL" in workflow
    assert "DEMO_PAYMENT_ENABLED=true" not in workflow
    assert "COMPOSE_FILE=compose.demo.yaml" in workflow


def test_demo_env_example_keeps_credentials_as_placeholders() -> None:
    env_example = (ROOT / ".env.demo.example").read_text(encoding="utf-8")

    assert "APP_ENV=demo" in env_example
    assert "CHATBOT_MODE=actual" in env_example
    assert "DEMO_PAYMENT_ENABLED=true" in env_example
    assert "DEMO_ACCOUNTS_ENABLED=true" in env_example
    assert "DEMO_ACCOUNT_PASSWORD=" in env_example
    assert "OPENAI_API_KEY=" in env_example
    assert "HF_TOKEN=" in env_example
    assert "SESSION_SECRET_KEY=" in env_example
    assert "FRONTEND_PORT=8501" in env_example
    assert "BACKEND_PORT=18000" in env_example


def test_ci_validates_demo_compose_and_deploy_script() -> None:
    workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")

    assert "cp .env.demo.example .env" in workflow
    assert "docker compose --env-file .env -f compose.demo.yaml config --quiet" in workflow
    assert "bash -n scripts/deploy_demo.sh" in workflow
