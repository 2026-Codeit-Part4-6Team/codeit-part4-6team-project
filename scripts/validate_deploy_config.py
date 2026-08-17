"""Validate deployment variables before they reach SSH or Docker commands."""

from __future__ import annotations

import os
import re
import sys
from pathlib import PurePosixPath
from urllib.parse import urlparse


def require_pattern(name: str, pattern: str) -> str:
    value = os.environ.get(name, "")
    if not re.fullmatch(pattern, value):
        raise ValueError(f"{name} has an invalid value")
    return value


def validate_deploy_path() -> None:
    value = require_pattern("VM_DEPLOY_PATH", r"/[A-Za-z0-9._/-]+")
    path = PurePosixPath(value)
    if ".." in path.parts or "//" in value:
        raise ValueError("VM_DEPLOY_PATH must be a normalized absolute path")


def validate_healthcheck_url() -> None:
    value = os.environ.get("PUBLIC_HEALTHCHECK_URL", "")
    parsed = urlparse(value)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or not re.fullmatch(r"[A-Za-z0-9.-]+", parsed.hostname)
    ):
        raise ValueError("PUBLIC_HEALTHCHECK_URL must be an HTTP(S) URL without credentials")


def validate() -> None:
    project_id = require_pattern("GCP_PROJECT_ID", r"[a-z][a-z0-9-]{4,28}[a-z0-9]")
    region = require_pattern("GCP_REGION", r"[a-z0-9-]+")
    repository = require_pattern("ARTIFACT_REGISTRY_REPOSITORY", r"[a-z0-9][a-z0-9._-]*")
    require_pattern(
        "GCP_WORKLOAD_IDENTITY_PROVIDER",
        r"projects/[0-9]+/locations/global/workloadIdentityPools/[A-Za-z0-9._-]+/providers/[A-Za-z0-9._-]+",
    )
    require_pattern(
        "GCP_SERVICE_ACCOUNT",
        r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.iam\.gserviceaccount\.com",
    )
    image_base = require_pattern(
        "IMAGE_BASE",
        r"[a-z0-9-]+-docker\.pkg\.dev/[a-z][a-z0-9-]+/[a-z0-9][a-z0-9._-]*",
    )
    expected_image_base = f"{region}-docker.pkg.dev/{project_id}/{repository}"
    if image_base != expected_image_base:
        raise ValueError("IMAGE_BASE does not match the configured GCP registry")
    require_pattern("IMAGE_TAG", r"[0-9a-f]{40}")
    require_pattern("VM_HOST", r"[A-Za-z0-9][A-Za-z0-9.-]*")
    require_pattern("VM_SSH_USER", r"[a-z_][a-z0-9_-]{0,31}")
    validate_deploy_path()

    compose_project = os.environ.get("COMPOSE_PROJECT_NAME") or "team6-app"
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]*", compose_project):
        raise ValueError("COMPOSE_PROJECT_NAME has an invalid value")

    validate_healthcheck_url()


def main() -> int:
    try:
        validate()
    except ValueError as error:
        print(f"deployment configuration error: {error}", file=sys.stderr)
        return 1
    print("Deployment configuration is valid.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
