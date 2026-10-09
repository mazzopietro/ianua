import logging
from fastapi import FastAPI

from ianua.api.exceptions import (
    AuthenticationRequiredError,
    InsufficientPermissionError,
    InvalidAuthenticationCredentialsError,
    authentication_required_handler,
    insufficient_permission_handler,
    invalid_authentication_credentials_handler,
    invalid_credentials_handler,
    invalid_refresh_token_handler,
    user_already_exists_handler,
    unexpected_error_handler,
)

from ianua.api.routes.health import router as health_router
from ianua.api.routes.auth import router as auth_router
from ianua.core.config import settings
from ianua.services.auth import (
    InvalidCredentialsError,
    InvalidRefreshTokenError,
    UserAlreadyExistsError,
)

from ianua.api.middleware import request_logging_middleware


logger = logging.getLogger("ianua")

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    debug=settings.debug,
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
    Exception,
    unexpected_error_handler,
)

app.include_router(health_router)
app.include_router(auth_router)