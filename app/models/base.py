"""Declarative base, naming conventions and shared mixins.

Read this before adding a model: the conventions here are what make Alembic's
autogenerate produce stable, reviewable migrations.
"""

from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import DateTime, MetaData, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from uuid_utils.compat import uuid7

# Deterministic names for every constraint and index.
#
# Without this, PostgreSQL invents names, and Alembic cannot tell an existing
# constraint from a new one — so autogenerate emits drop/create churn and
# downgrades break. Set once, never changed: renaming these later would make
# every existing migration unreproducible.
NAMING_CONVENTION = {
    "ix": "ix_%(table_name)s_%(column_0_name)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Base class for every model in the application."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)


def new_uuid() -> uuid.UUID:
    """Generate a UUIDv7 primary key.

    v7 embeds a timestamp in its high bits, so keys sort chronologically. That
    keeps B-tree index inserts at the right edge of the tree instead of
    scattering them like v4 does — the difference shows up as index bloat and
    write amplification once a table gets large.
    """
    return uuid7()


class UUIDPrimaryKeyMixin:
    """Adds a UUIDv7 primary key named `id`.

    UUIDs over auto-increment integers: ids can be generated before the INSERT,
    they do not leak row counts in URLs, and merging data across environments
    never collides.
    """

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)


class TimestampMixin:
    """Adds `created_at` / `updated_at`, both timezone-aware.

    Defaults are computed by the database (`server_default`), not by Python, so
    rows written by migrations, seeds or psql get correct timestamps too.
    """

    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
