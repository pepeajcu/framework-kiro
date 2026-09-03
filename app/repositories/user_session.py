"""Data access for server-side sessions."""

from __future__ import annotations

import datetime as dt
import uuid
from collections.abc import Sequence

from sqlalchemy import select, update

from app.models.user_session import UserSession
from app.repositories.base import BaseRepository
from app.security import hash_token


class UserSessionRepository(BaseRepository[UserSession]):
    """Sessions, always addressed by the hash of their token."""

    model = UserSession

    def get_by_token(self, token: str) -> UserSession | None:
        """Find the session a cookie token belongs to.

        Takes the raw token and hashes it here, so no caller is ever tempted to
        query with a plaintext token — the table does not store one.
        """
        stmt = select(UserSession).where(UserSession.token_hash == hash_token(token))
        return self.session.scalars(stmt).one_or_none()

    def list_active_for_user(self, user_id: uuid.UUID) -> Sequence[UserSession]:
        """Every session of this user that still authenticates."""
        now = dt.datetime.now(tz=dt.UTC)
        stmt = select(UserSession).where(
            UserSession.user_id == user_id,
            UserSession.revoked_at.is_(None),
            UserSession.expires_at > now,
        )
        return self.session.scalars(stmt).all()

    def revoke(self, session: UserSession) -> None:
        """Revoke one session."""
        session.revoked_at = dt.datetime.now(tz=dt.UTC)
        self.session.flush()

    def revoke_all_for_user(self, user_id: uuid.UUID) -> int:
        """Revoke every live session of a user, returning how many were closed.

        One UPDATE rather than a loop: this runs after a password change, when
        the point is that a stolen session stops working *now*.
        """
        now = dt.datetime.now(tz=dt.UTC)
        stmt = (
            update(UserSession)
            .where(
                UserSession.user_id == user_id,
                UserSession.revoked_at.is_(None),
            )
            .values(revoked_at=now)
            # RETURNING rather than reading `rowcount`: PostgreSQL gives the
            # affected rows back in the same round trip, and it is typed.
            .returning(UserSession.id)
        )
        revoked = self.session.scalars(stmt).all()
        self.session.flush()
        return len(revoked)

    def delete_expired(self, *, before: dt.datetime | None = None) -> int:
        """Remove sessions that expired, for a periodic cleanup.

        Nothing calls this yet. It exists because the table only grows
        otherwise, and finding that out in production is worse than reading it
        here.
        """
        cutoff = before or dt.datetime.now(tz=dt.UTC)
        expired = self.session.scalars(
            select(UserSession).where(UserSession.expires_at < cutoff)
        ).all()
        for session in expired:
            self.session.delete(session)
        self.session.flush()
        return len(expired)
