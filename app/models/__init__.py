"""SQLAlchemy models.

Every model must be imported here. Alembic's autogenerate only sees tables that
are registered on `Base.metadata`, and that only happens on import — a model
missing from this file produces migrations that silently drop its table.
"""

from app.models.base import Base

__all__ = ["Base"]
