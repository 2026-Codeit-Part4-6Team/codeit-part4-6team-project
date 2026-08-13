from ..graph.state import BasicState

VALID_PLATFORMS = {"instagram", "banner"}


def channel_node(state: BasicState) -> dict:
    platform = (state.get("platform") or "").strip().lower()
    if platform not in VALID_PLATFORMS:
        platform = "instagram"
    return {"platform": platform}
