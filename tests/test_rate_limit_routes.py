import uuid
from unittest.mock import AsyncMock

from redis.exceptions import ConnectionError as RedisConnectionError

from ianua.core.config import settings


def test_login_rate_limit_returns_429(db_client, monkeypatch):
    monkeypatch.setattr(settings, "redis_rate_limit_enabled", True)
    monkeypatch.setattr(
        settings,
        "redis_key_prefix",
        f"ianua-test-{uuid.uuid4().hex}",
    )

    payload = {
        "email": "mario@example.com",
        "password": "wrongPassword",
    }

    for _ in range(settings.rate_limit_login_requests):
        response = db_client.post("/auth/login", json=payload)
        assert response.status_code == 401

    response = db_client.post("/auth/login", json=payload)

    assert response.status_code == 429
    assert response.json() == {
        "code": "RATE_LIMIT_EXCEEDED",
        "message": "Too many requests",
    }

    assert int(response.headers["Retry-After"]) > 0

def test_register_rate_limit_returns_429(db_client, monkeypatch):
    monkeypatch.setattr(settings, "redis_rate_limit_enabled", True)
    monkeypatch.setattr(
        settings,
        "redis_key_prefix",
        f"ianua-test-{uuid.uuid4().hex}",
    )

    payload = {
        "email": "not-an-email",
        "password": "string123",
    }

    for _ in range(settings.rate_limit_register_requests):
        response = db_client.post("/auth/register", json=payload)
        assert response.status_code == 422

    response = db_client.post("/auth/register", json=payload)

    assert response.status_code == 429
    assert response.json() == {
        "code": "RATE_LIMIT_EXCEEDED",
        "message": "Too many requests",
    }

    assert int(response.headers["Retry-After"]) > 0

def test_refresh_rate_limit_returns_429(db_client, monkeypatch):
    monkeypatch.setattr(settings, "redis_rate_limit_enabled", True)
    monkeypatch.setattr(
        settings,
        "redis_key_prefix",
        f"ianua-test-{uuid.uuid4().hex}",
    )

    register_response = db_client.post(
        "/auth/register",
        json={
            "email": "mario@example.com",
            "password": "string123",
        },
    )
    
    assert register_response.status_code == 200

    login_response = db_client.post(
        "/auth/login",
        json={
            "email": "mario@example.com",
            "password": "string123",
        },
    )

    assert login_response.status_code == 200

    refresh_token = login_response.json()["refresh_token"]
    payload = {"refresh_token": refresh_token}

    for _ in range(settings.rate_limit_refresh_requests):
        response = db_client.post("/auth/refresh", json=payload)
        assert response.status_code == 200
        refresh_token = response.json()["refresh_token"]
        payload = {"refresh_token": refresh_token}

    response = db_client.post("/auth/refresh", json=payload)

    assert response.status_code == 429
    assert response.json() == {
        "code": "RATE_LIMIT_EXCEEDED",
        "message": "Too many requests",
    }
    assert int(response.headers["Retry-After"]) > 0

def test_login_returns_503_when_redis_becomes_unavailable(db_client, monkeypatch):
    monkeypatch.setattr(settings, "redis_rate_limit_enabled", True)

    redis_client = db_client.app.state.redis
    original_level = redis_client.eval

    monkeypatch.setattr(
        redis_client,
        "eval",
        AsyncMock(side_effect=RedisConnectionError("connection-failed")),
    )

    try:
        response = db_client.post(
            "/auth/login",
            json={
                "email": "mario@example.com",
                "password": "wrongPassword",
            },
        )
    finally:
        monkeypatch.setattr(redis_client, "eval", original_level)

    assert response.status_code == 503
    assert response.json() == {
        "code": "RATE_LIMITER_UNAVAILABLE",
        "message": "Rate limiting service is temporarily unavailable",
    }
    assert response.headers["Retry-After"] == "1"