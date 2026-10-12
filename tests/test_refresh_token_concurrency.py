from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import uuid4

from sqlalchemy import delete
from sqlalchemy.orm import Session

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
                