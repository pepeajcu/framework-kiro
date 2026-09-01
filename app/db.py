"""Database engine and session management.

Kiro uses SQLAlchemy 2.0 in **synchronous** mode. See
`docs/decisions/0002-sqlalchemy-sincrono.md` for why — do not convert this to
async without reading it first.
"""

from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings

_settings = get_settings()

engine = create_engine(
    str(_settings.database_url),
    # Verifies a pooled connection is still alive before handing it out.
    # Without it, connections killed by a restart or an idle timeout surface as
    # random "server closed the connection unexpectedly" errors on live traffic.
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
    # Recycle before the typical 1h idle cut-off of managed proxies.
    pool_recycle=1800,
    echo=False,
)

SessionFactory = sessionmaker(
    bind=engine,
    autoflush=False,
    # Attributes stay readable after commit. Without this, rendering a template
    # with an object that was just committed triggers a fresh SELECT per
    # attribute — or fails outright once the session is closed.
    expire_on_commit=False,
)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency yielding a request-scoped session.

    One session per request, committed on success and rolled back on any
    exception. Routers must not commit: the unit of work ends here, so a failure
    later in the request cannot leave a half-written transaction behind.
    """
    session = SessionFactory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
