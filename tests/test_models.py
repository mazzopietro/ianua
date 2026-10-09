import uuid
import time
import pytest

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from ianua.core.security import hash_password
from ianua.models import User

def test_user_timestamps_on_create(db_session):
    user = User(
        email="timestamps@example.com",
        password_hash=hash_password("password"),
    )

    db_session.add(user)
    db_session.flush()

    original_created_at = user.created_at
    original_updated_at = user.updated_at

    time.sleep(0.01)

    user.email = "updated@example.com"
    db_session.flush()

    db_session.refresh(user)

    assert user.created_at == original_created_at
    assert user.updated_at > original_updated_at

def test_user_role_rejects_invalid_value(db_session):
    user = User(
        email="invalid-role@example.com",
        password_hash=hash_password("password"),
        role="superadmin",
    )

    db_session.add(user)

    with pytest.raises(IntegrityError):
        db_session.flush()

    db_session.rollback()

def test_user_is_active_defaults_to_true(db_session):
    user = User(
        email="active-default@example.com",
        password_hash=hash_password("password"),
    )

    db_session.add(user)
    db_session.flush()

    assert user.is_active is True

def test_user_is_active_has_database_default(db_session):
    result = db_session.execute(
        text(
            """
            INSERT INTO users (id, email, password_hash)
            VALUES (:id, :email, :password_hash)
            RETURNING is_active
            """
        ),
        {
            "id": uuid.uuid4(),
            "email": "database-default@example.com",
            "password_hash": hash_password("password"),
        },
    )

    is_active = result.scalar_one()

    assert is_active is True