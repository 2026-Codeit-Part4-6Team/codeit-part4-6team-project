import httpx
import pytest

from frontend.api_client import ApiClient


def test_health_returns_backend_status(monkeypatch):
    """컨테이너 연결 검증은 인증이나 DB 변경 없이 백엔드 상태를 확인합니다."""
    observed = {}

    def fake_get(url: str, *, timeout: float) -> httpx.Response:
        observed.update(url=url, timeout=timeout)
        return httpx.Response(
            200,
            json={"status": "ok"},
            request=httpx.Request("GET", url),
        )

    monkeypatch.setattr(httpx, "get", fake_get)

    result = ApiClient("http://backend:8000/", timeout=10).health()

    assert result == {"status": "ok"}
    assert observed == {"url": "http://backend:8000/health", "timeout": 10}


def test_health_raises_for_backend_error(monkeypatch):
    """백엔드 상태 확인 실패를 성공으로 오인하지 않습니다."""

    def fake_get(url: str, *, timeout: float) -> httpx.Response:
        del timeout
        return httpx.Response(
            503,
            json={"status": "unavailable"},
            request=httpx.Request("GET", url),
        )

    monkeypatch.setattr(httpx, "get", fake_get)

    with pytest.raises(httpx.HTTPStatusError):
        ApiClient("http://backend:8000").health()
