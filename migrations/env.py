"""Alembic environment.

The database URL and the target metadata both come from the application, not
from `alembic.ini`. That way migrations always run against the same database
the app talks to, and autogenerate always sees the same models.
"""

from __future__ import annotations

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.config import get_settings

# Importing the models package registers every table on Base.metadata.
# Autogenerate is blind to anything not imported here — a model missing from
# `app/models/__init__.py` gets silently dropped from migrations.
from app.models import Base

config = context.config

if config.config_file_name is not None:
    # disable_existing_loggers=False is not optional. The default is True, and
    # it sets `.disabled = True` on every logger that already exists and is not
    # named in alembic.ini — that is, on every logger the application created
    # before this ran.
    #
    # It fails silently and far from its cause. In the test suite, loggers
    # created at import time go quiet for the whole session and `caplog`
    # captures nothing. In production, a project that runs `alembic upgrade
    # head` at startup loses its application logs entirely, with no error to
    # explain it.
    fileConfig(config.config_file_name, disable_existing_loggers=False)

# The URL comes from the application, unless the caller already set one.
#
# The test suite points Alembic at the `<db>_test` database this way (see
# `tests/conftest.py`). Overwriting it unconditionally would migrate the
# DEVELOPMENT database instead and leave the test one empty — and the suite
# would keep passing until the first test that queries a table, with a failure
# that gives no hint about its cause.
if not config.get_main_option("sqlalchemy.url", None):
    config.set_main_option("sqlalchemy.url", str(get_settings().database_url))

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Emit SQL to stdout without connecting.

    Useful when a DBA must review or apply the statements by hand.
    """
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Apply migrations against a live connection."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            # Detect column type changes, not just added/removed columns.
            # Off by default, and its absence is why "I changed the column type
            # but autogenerate saw nothing" happens.
            compare_type=True,
            # Same for server-side defaults.
            compare_server_default=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
