import pytest

from models.basic.nodes.channel import channel_node


@pytest.mark.parametrize(
    ("state", "expected_platform"),
    [
        ({"platform": "instagram"}, "instagram"),
        ({"platform": "BANNER"}, "banner"),
        ({"platform": "blog"}, "instagram"),
        ({"platform": ""}, "instagram"),
        ({}, "instagram"),
    ],
    ids=[
        "valid_lowercase",
        "valid_uppercase_normalized",
        "unsupported_value",
        "empty_value",
        "missing_key",
    ],
)
def test_channel_node_normalizes_or_defaults_platform(state, expected_platform):
    assert channel_node(state) == {"platform": expected_platform}
