from ..graph.state import BasicState

VALID_PLATFORMS = {"instagram", "banner"}


def channel_node(state: BasicState) -> dict:
    """요청된 플랫폼 값을 검증하고, 지원하지 않는 값이면 기본값(instagram)으로 대체한다."""
    platform = (state.get("platform") or "").strip().lower()
    if platform not in VALID_PLATFORMS:
        platform = "instagram"
    return {"platform": platform}
