import uuid
from datetime import datetime, timedelta, timezone
from pwdlib import PasswordHash

import jwt
import hashlib
import secrets

from ianua.core.config import settings

password_hash = PasswordHash.recommended()

class InvalidTokenError(Exception):
    pass

def hash_password(password: str) -> str:
    return password_hash.hash(password)

def verify_password(password: str, hashed_password: str) -> bool:
    return password_hash.verify(password, hashed_password)

def create_access_token(user_id: str, token_version: int) -> str:
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_access_token_expire_minutes)

    payload = {
        "sub": user_id,
        "token_version": token_version,
        "exp": expires_at,
    }

    return jwt.encode(
        payload,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )

def decode_access_token(token: str) -> tuple[uuid.UUID, int]:
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
    except jwt.PyJWTError:
        raise InvalidTokenError() from None

    subject = payload.get("sub")
    token_version = payload.get("token_version")

    if subject is None or token_version is None:
        raise InvalidTokenError()

    try:
        user_id = uuid.UUID(subject)
        token_version = int(token_version)
    except (ValueError, TypeError):
        raise InvalidTokenError() from None

    return user_id, token_version

def generate_refresh_token() -> str:
    return secrets.token_urlsafe(32)

def hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()