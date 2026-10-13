from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import uuid4

from sqlalchemy import delete
from sqlalchemy.orm import Session

from ianua.core.security import hash_refresh_token
from ianua.repositories.refresh_token import RefreshTokenRepository
from ianua.models import RefreshToken, User
from ianua.schemas import UserCreate, UserLogin
from ianua.services.auth import (
    AuthService,
    InvalidRefreshTokenError,
)


def test_concurrent_refresh_only_succeeds_once(db_engine):
    email = f"{uuid4().hex}@example.com"
    password = "string123"

    with Session(db_engine) as session:
        service = AuthService(session)
        service.register(
            UserCreate(email=email, password=password)
        )
        _, original_refresh_token = service.login(
            UserLogin(email=email, password=password)
        )

    barrier = Barrier(2)

    def attempt_refresh():
        with Session(db_engine) as session:
            service = AuthService(session)
            barrier.wait(timeout=10)

            try:
                access_token, new_refresh_token = service.refresh(original_refresh_token)
                return ("success", access_token, new_refresh_token)
            except InvalidRefreshTokenError:
                session.rollback()
                return ("rejected", None, None)

    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [
                executor.submit(attempt_refresh),
                executor.submit(attempt_refresh),
            ]
            results = [future.result(timeout=20) for future in futures]

        successes = [r for r in results if r[0] == "success"]
        rejected = [r for r in results if r[0] == "rejected"]

        assert len(successes) == 1
        assert len(rejected) == 1
        assert successes[0][1] # Access token
        assert successes[0][2] # New refresh token

    finally:
        with Session(db_engine) as session:
            user = session.query(User).filter_by(email=email).one_or_none()

            if user is not None:
                session.execute(
                    delete(RefreshToken)
                    .where(
                        RefreshToken.user_id == user.id
                    )
                )
                session.delete(user)
                session.commit()

def test_concurrent_refresh_and_revoke_all_sessions(db_engine):
    email = f"{uuid4().hex}@example.com"
    password = "string123"

    with Session(db_engine) as session:
        service = AuthService(session)
        service.register(
            UserCreate(email=email, password=password)
        )
        _, original_refresh_token = service.login(
            UserLogin(email=email, password=password)
        )

    barrier = Barrier(2)

    def attempt_refresh():
        with Session(db_engine) as session:
            service = AuthService(session)
            barrier.wait(timeout=10)

            try:
                access_token, new_refresh_token = service.refresh(original_refresh_token)
                return ("success", access_token, new_refresh_token)
            except InvalidRefreshTokenError:
                session.rollback()
                return ("rejected", None, None)
            
    def attempt_revoke_all():
        with Session(db_engine) as session:
            service = AuthService(session)
            user = (
                session.query(User)
                .filter_by(email=email)
                .one()
            )
            barrier.wait(timeout=10)
            service.revoke_all_sessions(user)

            new_count = (
                session.query(RefreshToken)
                .filter(
                    RefreshToken.user_id == user.id,
                    RefreshToken.revoked_at.is_(None),
                )
                .count()
            )

            return "revoked"

    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            refresh_future = executor.submit(attempt_refresh)
            revoke_future = executor.submit(attempt_revoke_all)

            refresh_result = refresh_future.result(timeout=20)
            revoke_result = revoke_future.result(timeout=20)

            assert revoke_result == "revoked"
            assert refresh_result[0] in {"success", "rejected"}

            with Session(db_engine) as session:
                repository = RefreshTokenRepository(session)

                original = repository.get_by_hash(hash_refresh_token(original_refresh_token))

                assert original is not None
                assert original.revoked_at is not None, (
                    f"Il refresh token originale non è revocato. "
                    f"Refresh result: {refresh_result[0]}"
                )

                if refresh_result[0] == "success":
                    new_refresh_token = refresh_result[2]
                    new_token = repository.get_by_hash(hash_refresh_token(new_refresh_token))

                    assert new_token is not None
                    assert new_token.revoked_at is not None, (
                        "Il nuovo refresh token non è revocato dopo revoke_all_sessions"
                    )

    finally:
        with Session(db_engine) as session:
            user = (
                session.query(User)
                .filter_by(email=email)
                .one_or_none()
            )

            if user is not None:
                session.execute(
                    delete(RefreshToken)
                    .where(
                        RefreshToken.user_id == user.id
                    )
                )
                session.delete(user)
                session.commit()