from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_frontend_to_backend_smoke_uses_frontend_node_runtime() -> None:
    deploy_script = (ROOT / "scripts" / "deploy.sh").read_text(encoding="utf-8")

    assert "exec -T frontend node - < scripts/smoke_frontend_backend.js" in deploy_script
    assert "/app/.venv/bin/python" not in deploy_script


def test_ci_reuses_frontend_to_backend_smoke_script() -> None:
    ci_workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")

    assert "docker compose exec -T frontend node - < scripts/smoke_frontend_backend.js" in ci_workflow
