import logging
import pytest

from fastapi import FastAPI
from fastapi.testclient import TestClient

from ianua.api.exceptions import unexpected_error_handler

@pytest.fixture
def error_client() -> TestClient:
    app = FastAPI()
    app.add_exception_handler(Exception, unexpected_error_handler)

    @app.get("/test-error")
    async def test_error():
        raise RuntimeError("Sensitive internal detail")

    return TestClient(app, raise_server_exceptions=False)

def test_unexpected_error_returns_generic_500(
    error_client: TestClient,
) -> None:
    response = error_client.get("/test-error")

    assert response.status_code == 500
    assert response.json() == {
        "code": "INTERNAL_SERVER_ERROR",
        "message": "An unexpected error occurred",   
    }
    assert "Sensitive internal detail" not in response.text

def test_unexpected_error_is_logged(
    error_client: TestClient,
    caplog,
) -> None:
    with caplog.at_level(logging.ERROR, logger="ianua.errors"):
        response = error_client.get("/test-error")

    assert response.status_code == 500
    assert "Unhandled exception" in caplog.text
    assert "Sensitive internal detail" in caplog.text
    assert "RuntimeError" in caplog.text
