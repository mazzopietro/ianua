import logging

from fastapi import Request
from fastapi.responses import JSONResponse

from ianua.services.auth import (
    InvalidCredentialsError,
    InvalidRefreshTokenError,
    UserAlreadyExistsError,
)

logger = logging.getLogger("ianua.errors")

class AuthenticationRequiredError(Exception):
    pass

class InvalidAuthenticationCredentialsError(Exception):
    pass

class InsufficientPermissionError(Exception):
    pass

def error_response(
    status_code: int,
    code: str,
    message: str,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "code": code,
            "message": message,
        },
        headers=headers
    )

async def user_already_exists_handler(
    request: Request,
    exc: UserAlreadyExistsError,
):
    return error_response(
        status_code=409,
        code="USER_ALREADY_EXISTS",
        message="User already exists",
    )

async def invalid_credentials_handler(
    request: Request,
    exc: InvalidCredentialsError,
):
    return error_response(
        status_code=401,
        code="INVALID_CREDENTIALS",
        message="Invalid credentials",
    )

async def invalid_refresh_token_handler(
    request: Request,
    exc: InvalidRefreshTokenError,
):
    return error_response(
        status_code=401,
        code="INVALID_REFRESH_TOKEN",
        message="Invalid refresh token",
    )

async def authentication_required_handler(
    request: Request,
    exc: AuthenticationRequiredError,
):
    return error_response(
        status_code=401,
        code="AUTHENTICATION_REQUIRED",
        message="Authentication required",
        headers={"WWW-Authenticate": "Bearer"},
    )

async def invalid_authentication_credentials_handler(
    request: Request,
    exc: InvalidAuthenticationCredentialsError,
):
    return error_response(
        status_code=401,
        code="INVALID_AUTHENTICATION_CREDENTIALS",
        message="Invalid authentication credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

async def insufficient_permission_handler(
    request: Request,
    exc: InsufficientPermissionError,
):
    return error_response(
        status_code=403,
        code="INSUFFICIENT_PERMISSIONS",
        message="Admin access required",
    )

async def unexpected_error_handler(
        request: Request,
        exc: Exception,
) -> JSONResponse:
    request_id = getattr(request.state, "request_id", None)

    logger.error(
        "Unhandled exception request_id=%s method=%s path=%s",
        request_id,
        request.method,
        request.url.path,
        exc_info=(type(exc), exc, exc.__traceback__),
    )

    return error_response(
        status_code=500,
        code="INTERNAL_SERVER_ERROR",
        message="An unexpected error occurred",
    )