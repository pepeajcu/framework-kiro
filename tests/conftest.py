"""Shared test fixtures.

Two things this file guarantees, so no project has to rebuild them:

1. Tests run against a **separate database** (`<db>_test`), created on demand.
   A test suite must never be able to wipe development data.
2. Each test runs inside a transaction that is **rolled back** afterwards, so
   tests cannot leak state into each other and the suite stays order-independent.

The schema is built by running the real Alembic migrations, not
`create_all()`. That way a migration that does not reproduce the models is a
test failure rather than a production surprise.
"""

from __future__ import annotations

from collections.abc import Generator
from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session

from app.config import get_settings

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _test_database_url() -> str:
    """Derive the test database URL from the application's own configuration.

    Goes through `Settings` rather than reading `os.environ`, so `.env` is
    loaded exactly the way the app loads it. Reading the environment directly
    would mean `make test` only worked after manually sourcing `.env`.

    The database name gets a `_test` suffix: the suite must never be able to
    touch development data.
    """
    settings = get_settings()
    parsed = sa.engine.make_url(str(settings.database_url))
    test_url = parsed.set(database=f"{parsed.database}_test")
    # `str(url)` masks the password as '***'. Rendering it back into a
    # connection string needs hide_password=False, or every connection fails
    # with a confusing "password authentication failed".
    return test_url.render_as_string(hide_password=False)


@pytest.fixture(scope="session")
def engine() -> Generator[Engine, None, None]:
    """Session-wide engine bound to a freshly migrated test database."""
    test_url = _test_database_url()
    parsed = sa.engine.make_url(test_url)

    # Connect to the maintenance database to create the test one. CREATE
    # DATABASE cannot run inside a transaction, hence AUTOCOMMIT.
    admin_url = parsed.set(database="postgres").render_as_string(hide_password=False)
    admin = create_engine(admin_url, isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        exists = conn.execute(
            sa.text("SELECT 1 FROM pg_database WHERE datname = :name"),
            {"name": parsed.database},
        ).scalar()
        if not exists:
            conn.execute(sa.text(f'CREATE DATABASE "{parsed.database}"'))
    admin.dispose()

    # Point Alembic at the test database and bring it up to head.
    alembic_cfg = Config(str(PROJECT_ROOT / "alembic.ini"))
    alembic_cfg.set_main_option("script_location", str(PROJECT_ROOT / "migrations"))
    alembic_cfg.set_main_option("sqlalchemy.url", test_url)
    command.upgrade(alembic_cfg, "head")

    test_engine = create_engine(test_url)
    yield test_engine
    test_engine.dispose()


@pytest.fixture
def db_session(engine: Engine) -> Generator[Session, None, None]:
    """A session whose changes are rolled back when the test ends.

    The session joins an outer transaction that is never committed. Code under
    test may call `commit()` freely — it lands on a savepoint, so it behaves
    normally but leaves nothing behind.
    """
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint")

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """HTTP client whose requests share the test's transaction.

    Overriding `get_db` is what lets a test set up data and then see it through
    an HTTP request — without it, the request would open its own connection and
    find an empty database.
    """
    from app.db import get_db
    from app.main import create_app

    app = create_app()

    def override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
