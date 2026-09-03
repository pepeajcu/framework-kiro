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
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.emails import MemoryEmailSender
from app.models.user import User
from app.services.auth import AuthService

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
def mailbox() -> MemoryEmailSender:
    """Collects the emails a test causes to be sent.

    The `client` fixture wires it in, so any test with an HTTP client can assert
    on what was emailed — `mailbox.last.text` — without touching a network.
    """
    return MemoryEmailSender()


def override_dependencies(
    app: FastAPI,
    db_session: Session,
    mailbox: MemoryEmailSender,
    settings: Settings | None = None,
) -> None:
    """Point an app at the test's transaction and outbox.

    Overriding `get_db` is what lets a test set up data and then see it through
    an HTTP request — without it, the request would open its own connection and
    find an empty database. Exposed as a function, not just used by the `client`
    fixture, so a test that needs an app of its own (extra routes, different
    settings) does not have to rebuild the wiring.
    """
    from app.config import get_settings as get_settings_dependency
    from app.db import get_db
    from app.emails import get_email_sender

    def override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_email_sender] = lambda: mailbox
    if settings is not None:
        app.dependency_overrides[get_settings_dependency] = lambda: settings


@pytest.fixture
def client(db_session: Session, mailbox: MemoryEmailSender) -> Generator[TestClient, None, None]:
    """HTTP client whose requests share the test's transaction and outbox."""
    from app.main import create_app

    app = create_app()
    override_dependencies(app, db_session, mailbox)

    # Redirects are not followed: Kiro answers every form POST with a 303, and a
    # client that follows it silently turns "did the login work?" into "did the
    # home page render?". Pass follow_redirects=True on the call when a test
    # really wants the destination.
    with TestClient(app, follow_redirects=False) as test_client:
        yield test_client

    app.dependency_overrides.clear()


# --- Accounts ---------------------------------------------------------------

PASSWORD = "una contraseña larga de prueba"
"""The password every fixture account uses. Long enough to pass the minimum."""


@pytest.fixture
def auth(db_session: Session) -> AuthService:
    """The authentication service, wired to the test transaction."""
    return AuthService(db_session, get_settings())


@pytest.fixture
def user(auth: AuthService) -> User:
    """An ordinary account, with the default `user` role."""
    return auth.register(email="ana@example.com", password=PASSWORD, full_name="Ana")


@pytest.fixture
def admin(auth: AuthService, db_session: Session) -> User:
    """An account with the `admin` role."""
    from app.models.role import ADMIN_ROLE
    from app.repositories.user import RoleRepository

    account = auth.register(email="jefa@example.com", password=PASSWORD, full_name="Jefa")
    role = RoleRepository(db_session).get_by_slug(ADMIN_ROLE)
    assert role is not None, "el rol admin lo crea la primera migración"
    account.roles.append(role)
    db_session.flush()
    return account


@pytest.fixture
def logged_in_client(client: TestClient, user: User) -> TestClient:
    """A client that has been through the real login form.

    Through the form on purpose: a fixture that forged the cookie by hand would
    keep passing after the login flow broke.
    """
    response = client.post("/login", data={"email": user.email, "password": PASSWORD})
    assert response.status_code == 303, "el login de la fixture falló"
    return client
