"""Single-use tokens for the password recovery flow."""

from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.user import User


class PasswordResetToken(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A password reset link that has been emailed but not yet used.

    Three properties make this safe, and all three are enforced in
    `app/services/auth.py`:

    - **Hashed.** The table stores a SHA-256, never the token in the link. Read
      access to the database does not grant access to any account.
    - **Single use.** `used_at` is stamped when the password changes, so the
      link in the inbox stops working the moment it has served its purpose.
    - **Short-lived.** `expires_at` closes the window in which a forwarded or
      leaked email is still dangerous.
    """

    __tablename__ = "password_reset_tokens"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    expires_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True))
    used_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), default=None)

    user: Mapped[User] = relationship(lazy="joined")

    def is_usable(self, *, now: dt.datetime | None = None) -> bool:
        """Whether this token can still be redeemed."""
        now = now or dt.datetime.now(tz=dt.UTC)
        return self.used_at is None and self.expires_at > now
