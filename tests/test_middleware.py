import uuid

from fastapi.testclient import TestClient

def test_health_response_contains_request_id(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert "X-Request-ID" in response.headers
    uuid.UUID(response.headers["X-Request-ID"])

def test_each_request_gets_a_unique_id(client: TestClient) -> None:
    first_response = client.get("/health")
    second_response = client.get("/health")

    first_id = first_response.headers["X-Request-ID"]
    second_id = second_response.headers["X-Request-ID"]

    assert first_id != second_id