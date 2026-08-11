import os
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
VALID_ENV = {
    "GCP_PROJECT_ID": "team6-project",
    "GCP_REGION": "asia-northeast3",
    "ARTIFACT_REGISTRY_REPOSITORY": "team6-app",
    "GCP_WORKLOAD_IDENTITY_PROVIDER": (
        "projects/123456789/locations/global/workloadIdentityPools/github/providers/team6"
    ),
    "GCP_SERVICE_ACCOUNT": "github-actions@team6-project.iam.gserviceaccount.com",
    "IMAGE_BASE": "asia-northeast3-docker.pkg.dev/team6-project/team6-app",
    "IMAGE_TAG": "a" * 40,
    "VM_HOST": "203.0.113.10",
    "VM_SSH_USER": "deploy",
    "VM_DEPLOY_PATH": "/srv/team6/app",
    "COMPOSE_PROJECT_NAME": "team6-app",
    "PUBLIC_HEALTHCHECK_URL": "https://app.example.com/_stcore/health",
}


def run_validator(overrides: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.update(VALID_ENV)
    env.update(overrides or {})
    return subprocess.run(
        [sys.executable, "scripts/validate_deploy_config.py"],
        cwd=PROJECT_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def test_accepts_expected_deployment_configuration() -> None:
    result = run_validator()

    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("VM_DEPLOY_PATH", "/srv/team6/app'; touch /tmp/owned; #"),
        ("IMAGE_BASE", "registry.example/team6'; touch /tmp/owned; #"),
        ("COMPOSE_PROJECT_NAME", "team6'; touch /tmp/owned; #"),
        ("VM_SSH_USER", "-oProxyCommand=touch_/tmp/owned"),
    ],
)
def test_rejects_values_that_can_break_remote_shell_quoting(name: str, value: str) -> None:
    result = run_validator({name: value})

    assert result.returncode != 0
    assert name in result.stderr
