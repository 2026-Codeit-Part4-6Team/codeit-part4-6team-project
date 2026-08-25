import logging

from ..graph.state import BasicState

logger = logging.getLogger(__name__)

VALID_PLATFORMS = {"instagram", "xbanner"}
_DEPRECATED_PLATFORM = {"banner": "xbanner"}


def channel_node(state: BasicState) -> dict:
    """요청된 플랫폼 값을 검증하고, 지원하지 않는 값이면 기본값(instagram)으로 대체한다.
    banner는 구버전 명칭이라 xbanner로 흡수한다."""
    platform = (state.get("platform") or "").strip().lower()
    if platform in _DEPRECATED_PLATFORM:
        mapped = _DEPRECATED_PLATFORM[platform]
        logger.warning("deprecated platform=%r 수신 — %r로 흡수", platform, mapped)
        platform = mapped
    if platform not in VALID_PLATFORMS:
        platform = "instagram"
    return {"platform": platform}