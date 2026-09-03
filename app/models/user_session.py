"""Server-side sessions.

Named `UserSession`, not `Session`: this codebase is full of
`sqlalchemy.orm.Session`, and two things called Session in the same file is how
an afternoon disappears.
"""

from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.user import User


class UserSession(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One logged-in browser.

    The row is what makes a session revocable — the whole reason Kiro keeps
    sessions in the database instead of encoding them in a JWT. Logging someone
    out, or cutting off a stolen laptop, is an UPDATE. With a self-contained
    token it is impossible until the token expires on its own.

    The cookie carries a random token; this table stores only its SHA-256. A
    dump of the database therefore hands the reader no usable session.
    """

    __tablename__ = "user_sessions"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )
    # 64 hex characters: the length of a SHA-256 digest.
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)

    expires_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    last_seen_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    # Enough to recognise your own sessions in a "where you are logged in" list.
    # 45 characters holds an IPv6 address; both default to empty because neither
    # is always available and neither is worth failing a login over.
    ip_address: Mapped[str] = mapped_column(String(45), default="", server_default="")
    user_agent: Mapped[str] = mapped_column(String(255), default="", server_default="")

    # `joined` because resolving a session and then loading its user is two
    # queries on every single request; this makes it one.
    user: Mapped[User] = relationship(lazy="joined")

    def is_usable(self, *, now: dt.datetime | None = None) -> bool:
        """Whether this session still authenticates anyone."""
        now = now or dt.datetime.now(tz=dt.UTC)
        return self.revoked_at is None and self.expires_at > now
