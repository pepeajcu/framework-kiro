"""Roles and the table that ties them to users."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Column, ForeignKey, String, Table
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.user import User

# Association table. A plain Table rather than a model because it carries no
# data of its own — adding a column here (who granted the role, when) is the
# signal to promote it to a real model.
user_roles = Table(
    "user_roles",
    Base.metadata,
    Column("user_id", ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("role_id", ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
)

ADMIN_ROLE = "admin"
USER_ROLE = "user"


class Role(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A named set of permissions.

    Kiro ships two, created by the first migration: `admin` and `user`. Add your
    own with a migration — code checks roles by slug, so a role that only exists
    in one environment is a bug waiting for a deploy.
    """

    __tablename__ = "roles"

    slug: Mapped[str] = mapped_column(String(50), unique=True)
    name: Mapped[str] = mapped_column(String(80))

    users: Mapped[list[User]] = relationship(secondary=user_roles, back_populates="roles")

    def __repr__(self) -> str:
        return f"<Role {self.slug}>"
