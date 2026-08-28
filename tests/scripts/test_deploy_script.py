from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_frontend_to_backend_smoke_uses_frontend_node_runtime() -> None:
    deploy_script = (ROOT / "scripts" / "deploy.sh").read_text(encoding="utf-8")

    assert 'exec -T frontend node - <<\'JS\'' in deploy_script
    assert "/app/.venv/bin/python" not in deploy_script

