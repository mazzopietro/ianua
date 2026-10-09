from datetime import datetime, timedelta, timezone
from unittest.mock import Mock

import pytest
from sqlalchemy.exc import IntegrityError

from ianua.core.security import (
    generate_refresh_token,
    hash_refresh_token,
    hash_password,
    verify_password,
)
from ianua.models import RefreshToken, User
from ianua.schemas import UserCreate
from ianua.services.auth import (
    AuthService,
    InvalidRefreshTokenError,
    InvalidCredentialsError,
    UserAlreadyExistsError,
)

def test_register_rolls_back_on_integrity_error():
    session = Mock()
    session.scalar.return_value = None
    
    session.commit.side_effect = IntegrityError(
        "duplicate email",
        None,
        None,
    )

    service = AuthService(session)

    data = UserCreate(
        email="mario@example.com",
        password="string123",
    )

    with pytest.raises(UserAlreadyExistsError):
        service.register(data)

    session.rollback.assert_called_once()

def test_refresh_returns_new_access_token(db_client, db_session):
    register_response = db_client.post(
        "/auth/register",
        json={
            "email": "mario@example.com",
            "password": "Password123!",
        },
    )

    assert register_response.status_code == 200

    login_response = db_client.post(
        "/auth/login",
        json={
            "email": "mario@example.com",
            "password": "Password123!",
        },
    )

    refresh_token = login_response.json()["refresh_token"]

    service = AuthService(db_session)

    access_token = service.refresh(refresh_token)

    assert access_token

def test_refresh_rejects_unknown_token(db_session):
    service = AuthService(db_session)

    with pytest.raises(InvalidRefreshTokenError):
        service.refresh("this-token-does-not-exist")

def test_refresh_rejects_expired_token(db_session):
    user = User(
        email = "mario@example.com",
        password_hash = "not-used",
    )

    db_session.add(user)
    db_session.flush()

    refresh_token = generate_refresh_token()

    stored_token = RefreshToken(
        user_id = user.id,
        token_hash = hash_refresh_token(refresh_token),
        expires_at = datetime.now(timezone.utc) - timedelta(days=1),
    )

    db_session.add(stored_token)
    db_session.flush()

    service = AuthService(db_session)

    with pytest.raises(InvalidRefreshTokenError):
        service.refresh(refresh_token)

def test_refresh_rejects_revoked_token(db_session):
    user = User(
        email = "mario@example.com",
        password_hash = "not-used",
    )

    db_session.add(user)
    db_session.flush()

    refresh_token = generate_refresh_token()

    stored_token = RefreshToken(
        user_id = user.id,
        token_hash = hash_refresh_token(refresh_token),
        expires_at = datetime.now(timezone.utc) + timedelta(days=1),
        revoked_at = datetime.now(timezone.utc),
    )

    db_session.add(stored_token)
    db_session.flush()

    service = AuthService(db_session)

    with pytest.raises(InvalidRefreshTokenError):
        service.refresh(refresh_token)

def test_refresh_rejects_inactive_user(db_session):
    user = User(
        email="mario@example.com",
        password_hash="not-used",
        is_active=False,
    )

    db_session.add(user)
    db_session.flush()

    refresh_token = generate_refresh_token()

    stored_token = RefreshToken(
        user_id=user.id,
        token_hash=hash_refresh_token(refresh_token),
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
    )

    db_session.add(stored_token)
    db_session.flush()

    service = AuthService(db_session)

    with pytest.raises(InvalidRefreshTokenError):
        service.refresh(refresh_token)

def test_logout_revokes_refresh_token(db_session):
    user = User(
        email="mario@example.com",
        password_hash="not-used",
    )

    db_session.add(user)
    db_session.flush()

    refresh_token = generate_refresh_token()

    stored_token = RefreshToken(
        user_id=user.id,
        token_hash=hash_refresh_token(refresh_token),
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
    )

    db_session.add(stored_token)
    db_session.flush()

    service = AuthService(db_session)

    service.logout(refresh_token)

    db_session.refresh(stored_token)

    assert stored_token.revoked_at is not None

    with pytest.raises(InvalidRefreshTokenError):
        service.refresh(refresh_token)

def test_cleanup_refresh_tokens(db_session):
    user = User(
        email="mario@example.com",
        password_hash="not-used",
    )

    db_session.add(user)
    db_session.flush()

    now = datetime.now(timezone.utc)

    expired_token = RefreshToken(
        user_id = user.id,
        token_hash = hash_refresh_token("expired"),
        expires_at = now - timedelta(days=1),
    )

    revoked_token = RefreshToken(
        user_id = user.id,
        token_hash = hash_refresh_token("revoked"),
        expires_at = now + timedelta(days=7),
        revoked_at = now,
    )

    valid_token = RefreshToken(
        user_id = user.id,
        token_hash = hash_refresh_token("valid"),
        expires_at = now + timedelta(days=7),
    )

    db_session.add_all([
        expired_token,
        revoked_token,
        valid_token,
    ])
    db_session.flush()

    service = AuthService(db_session)

    deleted = service.cleanup_refresh_tokens()

    assert deleted == 2

    remaining = db_session.query(RefreshToken).all()

    assert len(remaining) == 1
    assert remaining[0].token_hash == hash_refresh_token("valid")

def test_revoke_all_sessions_increments_token_version(db_session):
    service = AuthService(db_session)

    user = User(
        email="mario@example.com",
        password_hash="fake-hash",
    )

    db_session.add(user)
    db_session.flush()

    assert user.token_version == 0

    refresh_token = generate_refresh_token()

    stored_token = RefreshToken(
        user_id=user.id,
        token_hash=hash_refresh_token(refresh_token),
        expires_at=datetime.now(timezone.utc) + timedelta(days=7)
    )

    db_session.add(stored_token)
    db_session.flush()

    assert stored_token.revoked_at is None

    service.revoke_all_sessions(user)

    assert user.token_version == 1
    assert stored_token.revoked_at is not None

def test_change_password_updates_password(db_session):
    service = AuthService(db_session)

    user = User(
        email="change-password@example.com",
        password_hash=hash_password("old-password"),
    )

    db_session.add(user)
    db_session.flush()

    service.change_password(
        user,
        "old-password",
        "new-password",
    )

    assert verify_password("new-password", user.password_hash)
    assert not verify_password("old-password", user.password_hash)

def test_change_password_rejects_wrong_current_password(db_session):
    service = AuthService(db_session)

    user = User(
        email="wrong-password@example.com",
        password_hash=hash_password("old-password"),

    )

    db_session.add(user)
    db_session.flush()

    with pytest.raises(InvalidCredentialsError):
        service.change_password(
            user,
            "wrong-password",
            "new-password",
        )

    assert verify_password("old-password", user.password_hash)
    assert not verify_password("new-password", user.password_hash)

def test_change_password_revokes_all_sessions(db_session):
    service = AuthService(db_session)

    user = User(
        email="revoke-password@example.com",
        password_hash=hash_password("old-password"),
    )

    db_session.add(user)
    db_session.flush()

    refresh_token = generate_refresh_token()

    stored_token = RefreshToken(
        user_id=user.id,
        token_hash=hash_refresh_token(refresh_token),
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
    )

    db_session.add(stored_token)
    db_session.flush()

    assert user.token_version == 0
    assert stored_token.revoked_at is None

    service.change_password(
        user,
        "old-password",
        "new-password",
    )

    assert user.token_version == 1
    assert stored_token.revoked_at is not None

    assert verify_password("new-password", user.password_hash)
    assert not verify_password("old-password", user.password_hash)

def test_deleting_user_cascades_refresh_tokens(db_session):
    from sqlalchemy import select
    
    user = User(
        email="delete-user@example.com",
        password_hash=hash_password("password"),
    )

    db_session.add(user)
    db_session.flush()

    refresh_token = RefreshToken(
        user_id=user.id,
        token_hash="a" * 64,
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
    )

    db_session.add(refresh_token)
    db_session.flush()

    refresh_token_id = refresh_token.id

    db_session.delete(user)
    db_session.flush()

    stored_token = db_session.scalar(
        select(RefreshToken).where(
            RefreshToken.id == refresh_token_id
        )
    )

    assert stored_token is None

    