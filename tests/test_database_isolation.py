"""Regression guards for `migrations/env.py`.

Not feature tests. Two bugs lived in that file, both silent, both found only by
using the framework rather than reading it:

1. It overwrote the URL that `conftest.py` had already set, so `alembic upgrade`
   migrated the development database and left the test one empty. Every test
   kept passing — there were no tables to query yet — and the damage surfaced
   much later, far from its cause.
2. It called `fileConfig()` with its default `disable_existing_loggers=True`,
   which switches off every logger the application had already created.

If these fail, that file is the place to look.
"""

from __future__ import annotations

import pytest
from sqlalchemy import Engine, text
from sqlalchemy.orm import Session

from app.config import get_settings

# Imported for its side effect: creating the `app.access` logger at collection
# time, which is *before* any fixture runs the migrations. That ordering is what
# makes the logging guard below meaningful — a logger created afterwards would
# be fresh and enabled no matter what.
from app.middleware.access_log import logger as access_logger
from tests.conftest import PROJECT_ROOT


def test_engine_points_at_the_test_database(engine: Engine) -> None:
    """The fixture engine must target `<db>_test`, not the configured database."""
    dev_database = str(get_settings().database_url).rsplit("/", maxsplit=1)[-1]

    assert engine.url.database == f"{dev_database}_test"
    assert engine.url.database != dev_database


def test_session_is_connected_to_the_test_database(db_session: Session) -> None:
    """Ask PostgreSQL itself, rather than trusting the configuration.

    A correct URL that somehow connects elsewhere would still be a bug, so this
    checks the live connection instead of the string that produced it.
    """
    connected_to = db_session.execute(text("SELECT current_database()")).scalar_one()

    assert connected_to.endswith("_test")


def test_migrations_ran_against_the_test_database(db_session: Session) -> None:
    """Alembic's bookkeeping table must exist here.

    Its absence means `alembic upgrade` ran somewhere else — which is exactly
    the bug this module exists to catch. This is the test that actually detects
    it; the two above only guard the fixture's own configuration.
    """
    versions = PROJECT_ROOT / "migrations" / "versions"
    if not list(versions.glob("*.py")):
        pytest.skip("aún no hay migraciones: no hay nada que verificar")

    exists = db_session.execute(text("SELECT to_regclass('public.alembic_version')")).scalar()

    assert exists is not None, (
        "las migraciones no se aplicaron a la base de test. "
        "Comprueba que migrations/env.py respeta la URL que fija su llamador."
    )


def test_migrations_do_not_switch_off_application_loggers(engine: Engine) -> None:
    """Running Alembic must leave the application's loggers alone.

    `fileConfig()` disables every existing logger unless told otherwise. The
    failure is invisible: no error, no warning, just an application that stops
    logging. In a project that runs `alembic upgrade head` on startup, that is
    every log line it was ever going to write.
    """
    assert not access_logger.disabled, (
        "las migraciones desactivaron los loggers de la aplicación. "
        "migrations/env.py debe llamar a fileConfig(..., disable_existing_loggers=False)."
    )
