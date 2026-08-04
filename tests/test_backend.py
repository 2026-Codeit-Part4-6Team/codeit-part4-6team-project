from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


def test_health() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_generate() -> None:
    response = client.post("/generate", json={"prompt": "신메뉴 광고"})

    assert response.status_code == 200
    assert "신메뉴 광고" in response.json()["result"]
