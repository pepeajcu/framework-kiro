"""Data access for users and roles."""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import select

from app.models.role import Role
from app.models.user import User
from app.repositories.base import BaseRepository


def normalise_email(email: str) -> str:
    """Bring an address to the one form the database stores.

    Every write and every lookup goes through this. Skipping it at one call site
    is enough to create a second account for the same person, or to lock them
    out of the first one.
    """
    return email.strip().lower()


class UserRepository(BaseRepository[User]):
    """Users, always addressed by their normalised email."""

    model = User

    def get_by_email(self, email: str) -> User | None:
        """Find a user by email, case-insensitively."""
        stmt = select(User).where(User.email == normalise_email(email))
        return self.session.scalars(stmt).one_or_none()

    def email_exists(self, email: str) -> bool:
        """Whether an account already uses this address."""
        return self.get_by_email(email) is not None

    def create(self, **values: object) -> User:
        """Create a user, normalising the email first."""
        email = values.get("email")
        if isinstance(email, str):
            values["email"] = normalise_email(email)
        return super().create(**values)


class RoleRepository(BaseRepository[Role]):
    """Roles. Fixed reference data — created by a migration, not at runtime."""

    model = Role

    def get_by_slug(self, slug: str) -> Role | None:
        """Find a role by its slug."""
        stmt = select(Role).where(Role.slug == slug)
        return self.session.scalars(stmt).one_or_none()

    def get_by_slugs(self, slugs: Sequence[str]) -> Sequence[Role]:
        """Find several roles at once."""
        stmt = select(Role).where(Role.slug.in_(slugs))
        return self.session.scalars(stmt).all()
