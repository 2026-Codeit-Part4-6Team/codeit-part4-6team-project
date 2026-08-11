from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

from backend.main import app


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    """FastAPI 테스트 클라이언트를 생성하고 종료합니다."""
    with TestClient(app) as test_client:
        yield test_client
