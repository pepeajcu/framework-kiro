"""SQLAlchemy models.

Every model must be imported here. Alembic's autogenerate only sees tables that
are registered on `Base.metadata`, and that only happens on import — a model
missing from this file produces migrations that silently drop its table.
"""

from app.models.base import Base
from app.models.password_reset_token import PasswordResetToken
from app.models.role import ADMIN_ROLE, USER_ROLE, Role, user_roles
from app.models.user import User
from app.models.user_session import UserSession

__all__ = [
    "ADMIN_ROLE",
    "USER_ROLE",
    "Base",
    "PasswordResetToken",
    "Role",
    "User",
    "UserSession",
    "user_roles",
]
