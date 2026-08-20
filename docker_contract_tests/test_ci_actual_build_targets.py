from pathlib import Path
import tomllib


def test_sentence_transformers_belongs_to_basic_group():
    config = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))

    project_dependencies = config["project"].get("dependencies", [])
    basic_dependencies = config["dependency-groups"]["basic"]

    assert not any(dep.startswith("sentence-transformers") for dep in project_dependencies)
    assert any(dep.startswith("sentence-transformers") for dep in basic_dependencies)


def test_backend_dockerfile_has_lightweight_ci_and_actual_targets_with_uv_cache():
    dockerfile = Path("backend/Dockerfile").read_text(encoding="utf-8")

    assert " AS base" in dockerfile
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


def test_compose_defaults_to_actual_but_ci_workflow_uses_ci_target():
    compose = Path("compose.yaml").read_text(encoding="utf-8")
    workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")

    assert "target: ${BACKEND_BUILD_TARGET:-actual}" in compose
    assert "BACKEND_BUILD_TARGET: ci" in workflow
