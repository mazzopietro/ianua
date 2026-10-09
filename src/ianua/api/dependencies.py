from collections.abc import Generator
from typing import Callable

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from ianua.api.exceptions import (
    AuthenticationRequiredError,
    InsufficientPermissionError, 
    InvalidAuthenticationCredentialsError,
)

from ianua.core.database import SessionLocal
from ianua.core.security import InvalidTokenError, decode_access_token
from ianua.models import User, Role
from ianua.repositories import UserRepository

bearer_scheme = HTTPBearer(auto_error=False)

def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()

def get_current_user(
        credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
        db: Session = Depends(get_db),
):

    if credentials is None:
        raise AuthenticationRequiredError()

    token = credentials.credentials

    try:
        user_id, token_version = decode_access_token(token)
    except InvalidTokenError:
        raise InvalidAuthenticationCredentialsError() from None

    repository = UserRepository(db)
    user = repository.get_by_id(user_id)

    if user is None or not user.is_active:
        raise InvalidAuthenticationCredentialsError()

    if user.token_version != token_version:
        raise InvalidAuthenticationCredentialsError()

    return user

def require_roles(*roles: Role) -> Callable:
    def role_checker(
            current_user: User = Depends(get_current_user)
    ) -> User:
        if current_user.role not in roles:
            raise InsufficientPermissionError()

        return current_user

    return role_checker