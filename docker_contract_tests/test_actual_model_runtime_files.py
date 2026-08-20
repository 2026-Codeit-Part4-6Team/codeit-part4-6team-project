from pathlib import Path


def test_backend_dockerfile_copies_actual_model_runtime_packages():
    dockerfile = Path("backend/Dockerfile").read_text(encoding="utf-8")

    for source in ("models", "cache", "validation", "shared_data"):
        assert f"COPY {source} ./{source}" in dockerfile, source
