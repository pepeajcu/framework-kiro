"""Data access for password reset tokens."""

from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import select, update

from app.models.password_reset_token import PasswordResetToken
from app.repositories.base import BaseRepository
from app.security import hash_token


class PasswordResetTokenRepository(BaseRepository[PasswordResetToken]):
    """Reset tokens, always addressed by hash."""

    model = PasswordResetToken

    def get_by_token(self, token: str) -> PasswordResetToken | None:
        """Find the token record for a raw token from a reset link."""
        stmt = select(PasswordResetToken).where(PasswordResetToken.token_hash == hash_token(token))
        return self.session.scalars(stmt).one_or_none()

    def mark_used(self, token: PasswordResetToken) -> None:
        """Stamp a token as spent, so its link stops working."""
        token.used_at = dt.datetime.now(tz=dt.UTC)
        self.session.flush()

    def invalidate_all_for_user(self, user_id: uuid.UUID) -> int:
        """Spend every outstanding token of a user.

        Called when a password changes: any other reset link already sitting in
        an inbox must stop working, whether it was requested by the owner or by
        somebody trying to get in.
        """
        stmt = (
            update(PasswordResetToken)
            .where(
                PasswordResetToken.user_id == user_id,
                PasswordResetToken.used_at.is_(None),
            )
            .values(used_at=dt.datetime.now(tz=dt.UTC))
            .returning(PasswordResetToken.id)
        )
        spent = self.session.scalars(stmt).all()
        self.session.flush()
        return len(spent)
