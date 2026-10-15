import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from redis.asyncio import Redis
from redis.exceptions import RedisError

from ianua.api.exceptions import (
    AuthenticationRequiredError,
    InsufficientPermissionError,
    InvalidAuthenticationCredentialsError,
    authentication_required_handler,
    insufficient_permission_handler,
    invalid_authentication_credentials_handler,
    invalid_credentials_handler,
    invalid_refresh_token_handler,
    rate_limiter_exceeded_handler,
    rate_limiter_unavailable_handler,
    unexpected_error_handler,
    user_already_exists_handler,
)
from ianua.api.middleware import request_logging_middleware
from ianua.api.routes.auth import router as auth_router
from ianua.api.routes.health import router as health_router
from ianua.core.config import settings
from ianua.core.rate_limit import (
    RateLimiterExceededError,
    RateLimiterUnavailableError,
)
from ianua.services.auth import (
    InvalidCredentialsError,
    InvalidRefreshTokenError,
    UserAlreadyExistsError,
)

logger = logging.getLogger("ianua")

@asynccontextmanager
async def lifespan(app: FastAPI):
    redis_client = Redis.from_url(settings.redis_url)

    try:
        await redis_client.ping()
    except RedisError:
        logger.exception("Redis connection failed")
        await redis_client.aclose()
        raise

    app.state.redis = redis_client

    try:
        yield
    finally:
        await redis_client.aclose()

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    debug=settings.debug,
    lifespan=lifespan,
)

logger.info(
    "Application configured: name=%s version=%s environment=%s",
    settings.app_name,
    settings.app_version,
    settings.environment
)

app.middleware("http")(request_logging_middleware)

app.add_exception_handler(
    UserAlreadyExistsError,
    user_already_exists_handler,
)

app.add_exception_handler(
    InvalidRefreshTokenError,
    invalid_refresh_token_handler,
)

app.add_exception_handler(
    InvalidCredentialsError,
    invalid_credentials_handler,
)

app.add_exception_handler(
    AuthenticationRequiredError,
    authentication_required_handler,
)

app.add_exception_handler(
    InvalidAuthenticationCredentialsError,
    invalid_authentication_credentials_handler,
)

app.add_exception_handler(
    InsufficientPermissionError,
    insufficient_permission_handler,
)

app.add_exception_handler(
    RateLimiterExceededError,
    rate_limiter_exceeded_handler,
)

app.add_exception_handler(
    RateLimiterUnavailableError,
    rate_limiter_unavailable_handler,
)

app.add_exception_handler(
    Exception,
    unexpected_error_handler,
)

app.include_router(health_router)
app.include_router(auth_router)