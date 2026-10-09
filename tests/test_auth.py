from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from ianua.core.security import hash_refresh_token
from ianua.models import User, Role, RefreshToken
from ianua.services.auth import AuthService

def test_register(db_client, db_session):
    response = db_client.post(
        "/auth/register",
        json = {
            "email": "mario@example.com",
            "password": "string123",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["email"] == "mario@example.com"
    assert data["is_active"] is True
    assert "id" in data
    assert "password" not in data
    assert "password_hash" not in data

    user = db_session.scalar(
        select(User).where(User.email == "mario@example.com")
    )

    assert user is not None
    assert user.password_hash != "string123"

def test_login(db_client):
    register_response = db_client.post(
        "/auth/register",
        json = {
            "email": "mario@example.com",
            "password": "string123",
        },
    )

    assert register_response.status_code == 200

    login_response = db_client.post(
        "/auth/login",
        json = {
            "email": "mario@example.com",
            "password": "string123",
        }
    )

    assert login_response.status_code == 200

    data = login_response.json()

    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
    assert len(data["access_token"]) > 0

def test_login_wrong_password(db_client):
    register_response = db_client.post(
        "/auth/register",
        json = {
            "email": "mario@example.com",
            "password": "string123",
        },
    )

    assert register_response.status_code == 200

    login_response = db_client.post(
        "/auth/login",
        json = {
            "email": "mario@example.com",
            "password": "wrongPassword",
        },
    )

    assert login_response.status_code == 401
    assert login_response.json() == {
        "code": "INVALID_CREDENTIALS",
        "message": "Invalid credentials",
    }

def test_login_unknown_user(db_client):
    response = db_client.post(
        "/auth/login",
        json = {
            "email": "unknown@example.com",
            "password": "string123",
        },
    )

    assert response.status_code == 401
    assert response.json() == {
        "code": "INVALID_CREDENTIALS",
        "message": "Invalid credentials",
    }

def test_login_persists_refresh_token(db_client, db_session):
    register_response = db_client.post(
        "/auth/register",
        json = {
            "email": "mario@example.com",
            "password": "string123",
        },
    )

    assert register_response.status_code == 200

    response = db_client.post(
        "/auth/login",
        json = {
            "email": "mario@example.com",
            "password": "string123",
        },
    )

    assert response.status_code == 200

    refresh_token = response.json()["refresh_token"]

    stored_tokens = db_session.query(RefreshToken).all()

    assert len(stored_tokens) == 1
    assert stored_tokens[0].token_hash != refresh_token
    assert stored_tokens[0].user_id is not None

def test_get_me(db_client):
    response = db_client.post(
        "/auth/register",
        json = {
            "email": "mario@example.com",
            "password": "string123",
        },
    )

    assert response.status_code == 200

    login_response = db_client.post(
        "/auth/login",
        json = {
            "email": "mario@example.com",
            "password": "string123",
        },
    )

    assert login_response.status_code == 200

    token = login_response.json()["access_token"]

    me_response = db_client.get(
        "/auth/me",
        headers = {
            "Authorization": f"Bearer {token}",
        },
    )

    assert me_response.status_code == 200

    data = me_response.json()

    assert data["email"] == "mario@example.com"
    assert data["is_active"] is True

def test_me_invalid_token(db_client):
    response = db_client.get(
        "/auth/me",
        headers = {
            "Authorization": "Bearer false-token",
        },
    )

    assert response.status_code == 401
    assert response.json() == {
        "code": "INVALID_AUTHENTICATION_CREDENTIALS",
        "message": "Invalid authentication credentials"
    }

def test_me_without_token_returns_401(db_client):
    response = db_client.get("/auth/me")

    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"

def test_me_returns_401_if_user_does_not_exist(db_client, db_session):
    register_response = db_client.post(
        "/auth/register",
        json = {
            "email": "mario@example.com",
            "password": "string123",
        },
    )

    assert register_response.status_code == 200

    token = db_client.post(
        "/auth/login",
        json = {
            "email": "mario@example.com",
            "password": "string123",
        },
    ).json()["access_token"]

    user = db_session.query(User).filter_by(
        email="mario@example.com"
    ).one()

    db_session.query(RefreshToken).filter_by(
        user_id=user.id
    ).delete()

    db_session.delete(user)
    db_session.flush()

    response = db_client.get(
        "/auth/me",
        headers = {
            "Authorization": f"Bearer {token}",
        },
    )

    assert response.status_code == 401

def test_register_duplicate_email(db_client):
    first_response = db_client.post(
        "/auth/register",
        json = {
            "email": "mario@example.com",
            "password": "string123",
        },
    )

    assert first_response.status_code == 200

    second_response = db_client.post(
        "/auth/register",
        json = {
            "email": "mario@example.com",
            "password": "string321",
        },
    )

    assert second_response.status_code == 409
    assert second_response.json() == {
        "code": "USER_ALREADY_EXISTS",
        "message": "User already exists",
    }

def test_inactive_user_cannot_login(db_client, db_session):
    register_response = db_client.post(
        "/auth/register",
        json = {
            "email": "inactive@example.com",
            "password": "string123",
        },
    )

    assert register_response.status_code == 200

    user = db_session.scalar(
        select(User).where(User.email == "inactive@example.com")
    )

    assert user is not None

    user.is_active = False
    db_session.commit()

    login_response = db_client.post(
        "/auth/login",
        json = {
            "email": "inactive@example.com",
            "password": "string123",
        },
    )

    assert login_response.status_code == 401
    assert login_response.json() == {
        "code": "INVALID_CREDENTIALS",
        "message": "Invalid credentials",
    }

def test_inactive_user_cannot_access_me(db_client, db_session):
    register_response = db_client.post(
        "/auth/register",
        json = {
            "email": "inactive-me@example.com",
            "password": "string123",
        },
    )
    
    assert register_response.status_code == 200

    login_response = db_client.post(
        "/auth/login",
        json={
            "email": "inactive-me@example.com",
            "password": "string123",
        },
    )

    assert login_response.status_code == 200

    token = login_response.json()["access_token"]

    user = db_session.scalar(
        select(User).where(User.email == "inactive-me@example.com")
    )

    assert user is not None

    user.is_active = False
    db_session.commit()

    me_response = db_client.get(
        "/auth/me",
        headers = {
            "Authorization": f"Bearer {token}",
        },
    )

    assert me_response.status_code == 401
    assert me_response.json() == {
        "code": "INVALID_AUTHENTICATION_CREDENTIALS",
        "message": "Invalid authentication credentials",
    }

def test_register_rejects_short_password(db_client):
    response = db_client.post(
        "/auth/register",
        json = {
            "email": "mario@example.com",
            "password": "short",
        },
    )

    assert response.status_code == 422

def test_register_normalizes_email(db_client):
    response = db_client.post(
        "/auth/register",
        json = {
            "email": "Mario@Example.COM",
            "password": "string123",
        },
    )

    assert response.status_code == 200
    assert response.json()["email"] == "mario@example.com"

def test_login_is_case_insensitive_for_email(db_client):
    register_response = db_client.post(
        "/auth/register",
        json = {
            "email": "mario@example.com",
            "password": "string123",
        },
    )

    assert register_response.status_code == 200

    login_response = db_client.post(
        "/auth/login",
        json = {
            "email": "MARIO@EXAMPLE.COM",
            "password": "string123",
        },
    )

    assert login_response.status_code == 200
    assert "access_token" in login_response.json()

def test_refresh_returns_new_access_token(db_client):
    register_response = db_client.post(
        "/auth/register",
        json = {
            "email": "mario@example.com",
            "password": "string123",
        },
    )

    assert register_response.status_code == 200

    login_response = db_client.post(
        "/auth/login",
        json = {
            "email": "mario@example.com",
            "password": "string123",
        },
    )

    assert login_response.status_code == 200

    refresh_token = login_response.json()["refresh_token"]

    response = db_client.post(
        "/auth/refresh",
        json = {
            "refresh_token": refresh_token,
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["access_token"]
    assert body["refresh_token"] != refresh_token
    assert body["token_type"] == "bearer"

def test_refresh_rejects_invalid_token(db_client):
    response = db_client.post(
        "/auth/refresh",
        json = {
            "refresh_token": "invalid-token",
        },
    )

    assert response.status_code == 401
    assert response.json()["code"] == "INVALID_REFRESH_TOKEN"

def test_refresh_rotates_refresh_token(db_client):
    register_response = db_client.post(
        "/auth/register",
        json = {
            "email": "mario@example.com",
            "password": "string123",
        },
    )

    assert register_response.status_code == 200

    login_response = db_client.post(
        "/auth/login",
        json = {
            "email": "mario@example.com",
            "password": "string123",
        },
    )

    assert login_response.status_code == 200

    old_refresh_token = login_response.json()["refresh_token"]

    first_refresh = db_client.post(
        "/auth/refresh",
        json = {
            "refresh_token": old_refresh_token,
        },
    )

    assert first_refresh.status_code == 200

    new_refresh_token = first_refresh.json()["refresh_token"]

    assert new_refresh_token != old_refresh_token

    second_refresh = db_client.post(
        "/auth/refresh",
        json = {
            "refresh_token": old_refresh_token,
        },
    )

    assert second_refresh.status_code == 401

    third_refresh = db_client.post(
        "/auth/refresh",
        json = {
            "refresh_token": new_refresh_token,
        },
    )

    assert third_refresh.status_code == 200

def test_logout_revokes_refresh_token(db_client):
    register_response = db_client.post(
        "/auth/register",
        json = {
            "email": "mario@example.com",
            "password": "string123",
        },
    )

    assert register_response.status_code == 200

    login_response = db_client.post(
        "/auth/login",
        json = {
            "email": "mario@example.com",
            "password": "string123",
        },
    )

    assert login_response.status_code == 200

    refresh_token = login_response.json()["refresh_token"]

    logout_response = db_client.post(
        "/auth/logout",
        json = {
            "refresh_token": refresh_token,
        },
    )

    assert logout_response.status_code == 204

    refresh_response = db_client.post(
        "/auth/refresh",
        json = {
            "refresh_token": refresh_token,
        },
    )

    assert refresh_response.status_code == 401

def test_logout_is_idempotent(db_client):
    response = db_client.post(
        "/auth/logout",
        json = {
            "refresh_token": "already-invalid-token",
        },
    )

    assert response.status_code == 204

def test_refresh_rejects_expired_token(db_client, db_session):
    register_response = db_client.post(
        "/auth/register",
        json = {
            "email": "mario@example.com",
            "password": "string123",
        },
    )

    assert register_response.status_code == 200

    login_response = db_client.post(
        "/auth/login",
        json = {
            "email": "mario@example.com",
            "password": "string123",
        },
    )

    assert login_response.status_code == 200
    refresh_token = login_response.json()["refresh_token"]

    stored_token = (
        db_session.query(RefreshToken)
        .filter_by(
            token_hash=hash_refresh_token(refresh_token)
        )
        .one()
    )

    stored_token.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)

    db_session.flush()

    refresh_response = db_client.post(
        "/auth/refresh",
        json = {
            "refresh_token": refresh_token,
        },
    )

    assert refresh_response.status_code == 401

def test_refresh_token_can_be_rotated_multiple_times(db_client):
    register_response = db_client.post(
        "/auth/register",
        json = {
            "email": "mario@example.com",
            "password": "string123",
        },
    )

    assert register_response.status_code == 200

    login_response = db_client.post(
        "/auth/login",
        json = {
            "email": "mario@example.com",
            "password": "string123",
        },
    )

    assert login_response.status_code == 200
    token_a = login_response.json()["refresh_token"]

    # A -> B
    first_refresh = db_client.post(
        "/auth/refresh",
        json = {
            "refresh_token": token_a,
        },
    )

    assert first_refresh.status_code == 200

    token_b = first_refresh.json()["refresh_token"]

    assert token_b != token_a

    # A è inutilizzabile
    old_token_response = db_client.post(
        "/auth/refresh",
        json = {
            "refresh_token": token_a,
        },
    )

    assert old_token_response.status_code == 401

    # B -> C
    second_refresh = db_client.post(
        "/auth/refresh",
        json = {
            "refresh_token": token_b,
        },
    )

    assert second_refresh.status_code == 200

    token_c = second_refresh.json()["refresh_token"]

    assert token_c != token_b
    assert token_c != token_a

    # Anche B ora è inutilizzabile
    old_token_response = db_client.post(
        "/auth/refresh",
        json = {
            "refresh_token": token_b
        },
    )

    assert old_token_response.status_code == 401

def test_admin_requires_authentcation(db_client):
    response = db_client.get("/auth/admin")

    assert response.status_code == 401

    assert response.json() == {
        "code": "AUTHENTICATION_REQUIRED",
        "message": "Authentication required",
    }

def test_admin_rejects_regular_user(db_client):
    register_response = db_client.post(
        "/auth/register",
        json = {
            "email": "mario@example.com",
            "password": "string123",
        },
    )

    assert register_response.status_code == 200

    login_response = db_client.post(
        "/auth/login",
        json = {
            "email": "mario@example.com",
            "password": "string123",
        },
    )

    assert login_response.status_code == 200

    access_token = login_response.json()["access_token"]

    response = db_client.get(
        "/auth/admin",
        headers={
            "Authorization": f"Bearer {access_token}",
        },
    )

    assert response.status_code == 403

    assert response.json() == {
        "code": "INSUFFICIENT_PERMISSIONS",
        "message": "Admin access required",
    }

def test_admin_allows_admin_user(db_client, db_session):
    register_response = db_client.post(
        "/auth/register",
        json = {
            "email": "admin@example.com",
            "password": "string123",
        },
    )

    assert register_response.status_code == 200

    user = (
        db_session.query(User)
        .filter_by(email="admin@example.com")
        .one()
    )

    user.role = Role.ADMIN
    db_session.flush()

    login_response = db_client.post(
        "/auth/login",
        json = {
            "email": "admin@example.com",
            "password": "string123",
        },
    )

    assert login_response.status_code == 200

    access_token = login_response.json()["access_token"]

    response = db_client.get(
        "/auth/admin",
        headers={
            "Authorization": f"Bearer {access_token}",
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["email"] == "admin@example.com"
    assert body["role"] == "admin"

def test_access_token_is_invalid_after_token_version_changes(db_client, db_session):
    register_response = db_client.post(
        "/auth/register",
        json = {
            "email": "mario@example.com",
            "password": "string123",
        },
    )

    assert register_response.status_code == 200

    login_response = db_client.post(
        "/auth/login",
        json = {
            "email": "mario@example.com",
            "password": "string123",
        },
    )

    assert login_response.status_code == 200

    access_token = login_response.json()["access_token"]

    response = db_client.get(
        "/auth/me",
        headers={
            "Authorization": f"Bearer {access_token}",
        },
    )

    assert response.status_code == 200

    user = (
        db_session.query(User)
        .filter_by(email="mario@example.com")
        .one()
    )

    user.token_version += 1
    db_session.flush()

    response_token_v1 = db_client.get(
        "/auth/me",
        headers={
            "Authorization": f"Bearer {access_token}",
        },
    )

    assert response_token_v1.status_code == 401
    assert response_token_v1.json() == {
        "code": "INVALID_AUTHENTICATION_CREDENTIALS",
        "message": "Invalid authentication credentials",
    }

def test_access_token_is_invalid_after_all_sessions_are_revoked(
    db_client,
    db_session,
):
    register_response = db_client.post(
        "/auth/register",
        json = {
            "email": "revoke-all@example.com",
            "password": "string123",
        },
    )

    assert register_response.status_code == 200

    login_response = db_client.post(
        "/auth/login",
        json = {
            "email": "revoke-all@example.com",
            "password": "string123",
        },
    )

    assert login_response.status_code == 200

    access_token = login_response.json()["access_token"]

    response_me = db_client.get(
        "/auth/me",
        headers={
            "Authorization": f"Bearer {access_token}",
        },
    )

    assert response_me.status_code == 200

    user = db_session.query(User).filter_by(
        email="revoke-all@example.com"
    ).one()

    service = AuthService(db_session)
    service.revoke_all_sessions(user)

    response_me_again = db_client.get(
        "/auth/me",
        headers={
            "Authorization": f"Bearer {access_token}",
        },
    )

    assert response_me_again.status_code == 401
    assert response_me_again.json()["code"] == "INVALID_AUTHENTICATION_CREDENTIALS"

def test_logout_all_revokes_current_access_token(db_client):
    register_response = db_client.post(
        "/auth/register",
        json = {
            "email": "logout-all@example.com",
            "password": "string123",
        },
    )

    assert register_response.status_code == 200

    login_response = db_client.post(
        "/auth/login",
        json = {
            "email": "logout-all@example.com",
            "password": "string123",
        },
    )

    assert login_response.status_code == 200

    access_token = login_response.json()["access_token"]

    response_me = db_client.get(
        "/auth/me",
        headers={
            "Authorization": f"Bearer {access_token}",
        },
    )

    assert response_me.status_code == 200

    logout_all_response = db_client.post(
        "/auth/logout-all",
        headers={
            "Authorization": f"Bearer {access_token}",
        },
    )

    assert logout_all_response.status_code == 204

    response_me_again = db_client.get(
        "/auth/me",
        headers={
            "Authorization": f"Bearer {access_token}",
        },
    )

    assert response_me_again.status_code == 401
    assert response_me_again.json()["code"] == "INVALID_AUTHENTICATION_CREDENTIALS"

def test_change_password_changes_password(db_client):
    register_response = db_client.post(
        "/auth/register",
        json = {
            "email": "change-password-api@example.com",
            "password": "old-password",
        },
    )

    assert register_response.status_code == 200

    login_response = db_client.post(
        "/auth/login",
        json = {
            "email": "change-password-api@example.com",
            "password": "old-password",
        },
    )

    assert login_response.status_code == 200

    access_token = login_response.json()["access_token"]

    change_response = db_client.post(
        "/auth/change-password",
        headers={
            "Authorization": f"Bearer {access_token}",
        },
        json={
            "current_password": "old-password",
            "new_password": "new-password",
        },
    )

    assert change_response.status_code == 204

    me_response = db_client.get(
        "/auth/me",
        headers={
            "Authorization": f"Bearer {access_token}",
        },
    )

    assert me_response.status_code == 401
    assert me_response.json() == {
        "code": "INVALID_AUTHENTICATION_CREDENTIALS",
        "message": "Invalid authentication credentials",
    }

    old_login_response = db_client.post(
        "/auth/login",
        json={
            "email": "change-password-api@example.com",
            "password": "old-password",
        },
    )

    assert old_login_response.status_code == 401

    new_login_response = db_client.post(
        "/auth/login",
        json={
            "email": "change-password-api@example.com",
            "password": "new-password",
        },
    )

    assert new_login_response.status_code == 200

def test_change_password_rejects_wrong_current_password(db_client):
    register_response = db_client.post(
        "/auth/register",
        json = {
            "email": "wrong-current-password@example.com",
            "password": "old-password",
        },
    )

    assert register_response.status_code == 200

    login_response = db_client.post(
        "/auth/login",
        json = {
            "email": "wrong-current-password@example.com",
            "password": "old-password",
        },
    )

    assert login_response.status_code == 200

    access_token = login_response.json()["access_token"]

    change_response = db_client.post(
        "/auth/change-password",
        headers={
            "Authorization": f"Bearer {access_token}",
        },
        json={
            "current_password": "wrong-password",
            "new_password": "new-password",
        },
    )

    assert change_response.status_code == 401
    assert change_response.json() == {
        "code": "INVALID_CREDENTIALS",
        "message": "Invalid credentials",
    }

def test_change_password_requires_authentication(db_client):
    response = db_client.post(
        "/auth/change-password",
        json={
            "current_password": "old-password",
            "new_password": "new-password",
        },
    )

    assert response.status_code == 401
    assert response.json() == {
        "code": "AUTHENTICATION_REQUIRED",
        "message": "Authentication required",
    }