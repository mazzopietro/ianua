from datetime import datetime, timedelta, timezone

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ianua.core.security import (
    create_access_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)
from ianua.models import RefreshToken, User
from ianua.repositories import RefreshTokenRepository, UserRepository
from ianua.schemas import UserCreate, UserLogin

class UserAlreadyExistsError(Exception):
    pass

class InvalidCredentialsError(Exception):
    pass

class InvalidRefreshTokenError(Exception):
    pass

class AuthService:
    def __init__(self, session: Session):
        self.session = session
        self.user_repository = UserRepository(session)
        self.refresh_token_repository = RefreshTokenRepository(session)

    def _commit(self) -> None:
        try:
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise

    def register(self, data: UserCreate) -> User:
        email = data.email.strip().lower()

        existing_user = self.user_repository.get_by_email(email)

        if existing_user is not None:
            raise UserAlreadyExistsError()

        user = User(
            email=email,
            password_hash=hash_password(data.password)
        )

        self.user_repository.create(user)

        try:
            self.session.commit()
        except IntegrityError:
            self.session.rollback()
            raise UserAlreadyExistsError() from None
        
        self.session.refresh(user)

        return user

    def login(self, data: UserLogin) -> tuple[str, str]:
        email = data.email.strip().lower()

        user = self.user_repository.get_by_email(email)

        if user is None:
            raise InvalidCredentialsError()

        if not verify_password(data.password, user.password_hash):
            raise InvalidCredentialsError()

        if not user.is_active:
            raise InvalidCredentialsError()

        access_token = create_access_token(
            str(user.id),
            user.token_version,
        )

        refresh_token = generate_refresh_token()

        refresh_token_model = RefreshToken(
            user_id = user.id,
            token_hash = hash_refresh_token(refresh_token),
            expires_at = datetime.now(timezone.utc) + timedelta(days=7),
        )

        self.refresh_token_repository.create(refresh_token_model)

        self._commit()

        return access_token, refresh_token

    def refresh(self, refresh_token: str) -> str:
        token_hash = hash_refresh_token(refresh_token)

        stored_token = self.refresh_token_repository.get_by_hash_for_update(token_hash)

        if stored_token is None:
            raise InvalidRefreshTokenError()

        if stored_token.revoked_at is not None:
            raise InvalidRefreshTokenError()

        if stored_token.expires_at <= datetime.now(timezone.utc):
            raise InvalidRefreshTokenError()

        user = self.user_repository.get_by_id(stored_token.user_id)

        if user is None or not user.is_active:
            raise InvalidRefreshTokenError()

        stored_token.revoked_at = datetime.now(timezone.utc)

        new_refresh_token = generate_refresh_token()

        new_refresh_token_model = RefreshToken(
            user_id=user.id,
            token_hash=hash_refresh_token(new_refresh_token),
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        )

        self.refresh_token_repository.create(new_refresh_token_model)

        access_token = create_access_token(
            str(user.id),
            user.token_version,
        )

        self._commit()

        return access_token, new_refresh_token

    def logout(self, refresh_token: str) -> None: 
        token_hash = hash_refresh_token(refresh_token)

        stored_token = self.refresh_token_repository.get_by_hash(token_hash)

        if stored_token is None:
            return

        if stored_token.revoked_at is not None:
            return

        self.refresh_token_repository.revoke(stored_token)

        self._commit()

    def cleanup_refresh_tokens(self) -> int:
        deleted = self.refresh_token_repository.delete_expired_and_revoked()

        self._commit()

        return deleted

    def _revoke_all_sessions(self, user: User) -> None:
        user.token_version += 1
        self.refresh_token_repository.revoke_all_for_user(user.id)

    def revoke_all_sessions(self, user: User) -> None:
        self._revoke_all_sessions(user)
        self._commit()

    def change_password(
        self,
        user: User,
        current_password: str,
        new_password: str,
    ) -> None:
        if not verify_password(current_password, user.password_hash):
            raise InvalidCredentialsError()

        user.password_hash = hash_password(new_password)
        self._revoke_all_sessions(user)
        self._commit()