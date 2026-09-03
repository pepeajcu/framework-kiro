"""The user account."""

from __future__ import annotations

from sqlalchemy import Boolean, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.role import Role, user_roles


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Someone who can log in.

    Emails are stored **lowercased and stripped**, and the unique constraint is
    what enforces one account per address. Normalisation happens in
    `UserRepository`, so it cannot be forgotten at one call site: without it,
    `Ana@example.com` and `ana@example.com` are two accounts, and the person who
    created the first one can never log in again.
    """

    __tablename__ = "users"

    # 254 is the maximum length of an email address per RFC 5321.
    email: Mapped[str] = mapped_column(String(254), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(120), default="", server_default="")

    # Deactivating beats deleting: rows all over the database point at a user,
    # and a deleted account takes its orders and its audit trail with it.
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("true"))

    # `selectin` loads every user's roles in one extra query instead of one per
    # user, and — more importantly here — before the template starts rendering.
    roles: Mapped[list[Role]] = relationship(
        secondary=user_roles,
        back_populates="users",
        lazy="selectin",
    )

    def has_role(self, slug: str) -> bool:
        """Whether this user holds the role with this slug."""
        return any(role.slug == slug for role in self.roles)

    def __repr__(self) -> str:
        return f"<User {self.email}>"
