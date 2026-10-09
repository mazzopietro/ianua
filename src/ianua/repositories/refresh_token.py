import uuid
from datetime import datetime, timezone

from sqlalchemy import select, delete, update
from sqlalchemy.orm import Session

from ianua.models.refresh_token import RefreshToken

class RefreshTokenRepository:
    def __init__(self, session: Session):
        self.session = session

    def create(self, refresh_token: RefreshToken) -> RefreshToken:
        self.session.add(refresh_token)
        self.session.flush()
        return refresh_token

    def get_by_hash(self, token_hash: str) -> RefreshToken | None:
        statement = select(RefreshToken).where(
            RefreshToken.token_hash == token_hash
        )
        return self.session.scalar(statement)

    def get_by_hash_for_update(self, token_hash: str) -> RefreshToken | None:
        statement = (
            select(RefreshToken)
            .where(RefreshToken.token_hash == token_hash)
            .with_for_update()
        )

        return self.session.scalar(statement)

    def revoke(self, refresh_token: RefreshToken) -> None:
        refresh_token.revoked_at = datetime.now(timezone.utc)

    def delete_expired_and_revoked(self) -> int:
        now = datetime.now(timezone.utc)

        statement = delete(RefreshToken).where(
            (RefreshToken.expires_at <= now)
            | (RefreshToken.revoked_at.is_not(None))
        )

        result = self.session.execute(statement)
        return result.rowcount or 0

    def revoke_all_for_user(self, user_id: uuid.UUID) -> int:
        now = datetime.now(timezone.utc)

        statement = (
            update(RefreshToken)
            .where(
                RefreshToken.user_id == user_id,
                RefreshToken.revoked_at.is_(None),
            )
            .values(revoked_at=now)
        )
        
        result = self.session.execute(statement)
        return result.rowcount or 0
