"""The test suite must never touch the development database.

This is a regression guard, not a feature test. `migrations/env.py` used to
overwrite the URL that `conftest.py` had already set, so `alembic upgrade`
migrated the development database and left the test one empty. Every test kept
passing — there were no tables to query yet — and the damage only surfaced
later, far from its cause.

If these fail, check that `env.py` still honours a URL set by its caller.
"""

from __future__ import annotations

import pytest
from sqlalchemy import Engine, text
from sqlalchemy.orm import Session

from app.config import get_settings
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

    exists = db_session.execute(
        text("SELECT to_regclass('public.alembic_version')")
    ).scalar()

    assert exists is not None, (
        "las migraciones no se aplicaron a la base de test. "
        "Comprueba que migrations/env.py respeta la URL que fija su llamador."
    )
