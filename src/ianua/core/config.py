from typing import Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str = "Ianua Auth Service"
    app_version: str = "0.1.0"
    environment: Literal["development", "test", "production"] = "development"
    debug: bool = False

    database_url: str
    test_database_url: str | None = None

    jwt_secret_key: str = Field(min_length=32)
    jwt_algorithm: Literal["HS256"] = "HS256"
    jwt_access_token_expire_minutes: int = Field(default=30, gt=0)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @model_validator(mode="after")
    def validate_environment_settings(self):
        if self.environment == "production" and self.debug:
            raise ValueError("DEBUG must be false in production")

        if self.environment == "test" and not self.test_database_url:
            raise ValueError("TEST_DATABASE_URL is required in test environment")

        if self.environment == "production":
            if self.jwt_secret_key.lower() in {
                "secret",
                "changeme",
                "replace-with-a-long-random-secret",
            }:
                raise ValueError("JWT_SECRET_KEY must be replaced in production")

        if self.test_database_url and (
            self.test_database_url == self.database_url
        ):
            raise ValueError(
                "TEST_DATABASE_URL must differ from DATABASE_URL"
            )

        return self

settings = Settings()