import httpx


class ApiClient:
    """프론트엔드에서 사용하는 백엔드 API 클라이언트입니다."""

    def __init__(self, base_url: str, timeout: float = 30.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def generate(self, prompt: str) -> dict:
        """광고 콘텐츠 생성을 요청합니다."""
        response = httpx.post(
            f"{self.base_url}/generate",
            json={"prompt": prompt},
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()
