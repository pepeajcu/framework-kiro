"""Shared FastAPI dependencies.

Import the aliases from here rather than wiring `Depends(...)` by hand in every
route: one definition, one place to change.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db import get_db
from app.emails import EmailSender, get_email_sender
from app.exceptions import AuthenticationRequiredError, PermissionDeniedError
from app.models.user import User
from app.security import SESSION_COOKIE_NAME, unsign_session_token
from app.services.auth import AuthService

DbSession = Annotated[Session, Depends(get_db)]
"""Request-scoped database session."""

AppSettings = Annotated[Settings, Depends(get_settings)]
"""Application configuration."""

Emailer = Annotated[EmailSender, Depends(get_email_sender)]
"""The configured transactional email sender.

Injected rather than imported so a test can swap it for `MemoryEmailSender`
through `app.dependency_overrides`."""


# --- Authentication ---------------------------------------------------------


def get_optional_user(
    request: Request,
    db: DbSession,
    settings: AppSettings,
) -> User | None:
    """Resolve the session cookie into a user, or None if nobody is logged in.

    Also stashes the result on `request.state`, which is where `render()` picks
    it up — that is what lets the site header know who is looking at it without
    every handler passing `user` into its template context.
    """
    user: User | None = None
    cookie = request.cookies.get(SESSION_COOKIE_NAME)

    if cookie is not None:
        token = unsign_session_token(cookie, settings)
        if token is not None:
            user = AuthService(db, settings).resolve_session(token)

    request.state.user = user
    return user


OptionalUser = Annotated[User | None, Depends(get_optional_user)]
"""The logged-in user, or None.

Declare it on every page handler, even public ones: it is what makes the header
render the right thing."""


def require_user(request: Request, user: OptionalUser) -> User:
    """The logged-in user, or a redirect to the login form.

    Raising rather than returning a response keeps the handler's signature
    honest — it declares a `User`, and it gets one or never runs.
    """
    if user is None:
        raise AuthenticationRequiredError(next_url=request.url.path)
    return user


CurrentUser = Annotated[User, Depends(require_user)]
"""The logged-in user. Anonymous visitors are redirected to /login."""


def require_role(slug: str) -> Callable[[User], User]:
    """Build a dependency that also demands a role.

        @router.get("/admin")
        def panel(request: Request, user: Annotated[User, Depends(require_role("admin"))]):
            ...

    Anonymous visitors are redirected to the login form; logged-in users without
    the role get a 403 page. Those are different situations and must not
    collapse into one: sending someone who is already logged in to a login form
    is a loop they cannot escape.
    """

    def dependency(user: CurrentUser) -> User:
        if not user.has_role(slug):
            raise PermissionDeniedError(f"role required: {slug}")
        return user

    return dependency
