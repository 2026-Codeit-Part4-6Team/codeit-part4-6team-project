from uuid import UUID

from fastapi.testclient import TestClient


def test_generate(client: TestClient) -> None:
    response = client.post("/generate", json={"prompt": "신메뉴 광고"})

    assert response.status_code == 200
    body = response.json()
    assert UUID(body["request_id"])
    assert body["status"] == "completed"
    assert "신메뉴 광고" in body["result"]["text"]


def test_generate_rejects_empty_prompt(client: TestClient) -> None:
    response = client.post("/generate", json={"prompt": ""})

    assert response.status_code == 422
