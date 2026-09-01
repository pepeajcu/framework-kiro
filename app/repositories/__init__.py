"""Data access layer.

**Every** database query lives here. Routers and services call repositories;
they never build SQLAlchemy statements themselves.

Why the rule exists: queries scattered across route handlers cannot be reused,
tested in isolation, or audited when a query turns out to be slow or wrong. One
layer means one place to look.
"""

from app.repositories.base import BaseRepository

__all__ = ["BaseRepository"]
