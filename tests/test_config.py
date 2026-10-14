import pytest
from pydantic import ValidationError

from ianua.core.config import Settings


def valid_settings(**overrides) -> dict:
    values = {
        "database_url": "postgresql+psycopg://user:password@localhost:5432/app",
        "test_database_url": "postgresql+psycopg://user:password@localhost:5432/app_test",
        "jwt_secret_key": "a" * 48,
        "environment": "development",
        "debug": False,
    }
    values.update(overrides)
    return values

def test_settings_accept_valid_configuration():
    settings = Settings(**valid_settings())

    assert settings.environment == "development"
    assert settings.debug is False
    assert settings.jwt_algorithm == "HS256"

def test_settings_reject_unknown_environment():
    with pytest.raises(ValidationError):
        Settings(**valid_settings(environment="staging"))

def test_settings_reject_debug_in_production():
    with pytest.raises(ValidationError):
        Settings(**valid_settings(environment="production", debug=True))

def test_settings_reject_short_jwt_secret():
    with pytest.raises(ValidationError):
        Settings(**valid_settings(jwt_secret_key="too-short"))

def test_explicit_values_override_environment(monkeypatch):
    monkeypatch.setenv("APP_NAME", "Name from environment")

    settings = Settings(
        **valid_settings(),
        app_name="Name from test",
    )

    assert settings.app_name == "Name from test"

def test_settings_reject_placeholder_secret_in_production():
    with pytest.raises(ValidationError):
        Settings(
            **valid_settings(
                environment="production",
                jwt_secret_key="replace-with-a-long-random-secret",
            )
        )

def test_settings_reject_same_database_for_tests_and_production():
    database_url = (
        "postgresql+psycopg://user:password@localhost:5432/app"
    )

    with pytest.raises(ValidationError):
        Settings(
            **valid_settings(
                database_url=database_url,
                test_database_url=database_url,
            )
        )

def test_settings_accept_default_rate_limit_configuration():
    settings = Settings(**valid_settings())

    assert settings.redis_url == "redis://localhost:6380/1"
    assert settings.redis_rate_limit_enabled is True
    assert settings.rate_limit_register_requests == 5
    assert settings.rate_limit_register_window_seconds == 900
    assert settings.rate_limit_login_requests == 10
    assert settings.rate_limit_login_window_seconds == 60
    assert settings.rate_limit_refresh_requests == 30
    assert settings.rate_limit_refresh_window_seconds == 60

def test_settings_reject_non_positive_rate_limit():
    with pytest.raises(ValidationError):
        Settings(**valid_settings(), rate_limit_login_requests=0)