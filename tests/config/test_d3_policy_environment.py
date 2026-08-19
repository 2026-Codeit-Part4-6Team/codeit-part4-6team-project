from pathlib import Path


def test_compose_passes_d3_policy_environment_to_backend():
    compose = (Path(__file__).parents[2] / "compose.yaml").read_text()
    for key, default in (
        ("DAILY_FREE_LIMIT", "10"),
        ("BASIC_CREDIT_COST", "50"),
        ("CONSULTANT_CREDIT_COST", "10"),
        ("MODEL_REQUEST_TIMEOUT_SECONDS", "60"),
    ):
        assert f"{key}: ${{{key}:-{default}}}" in compose
