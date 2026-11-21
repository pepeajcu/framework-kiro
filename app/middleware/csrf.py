"""CSRF protection, double-submit style.

The problem it solves: a form on somebody else's site can POST to yours, and the
browser attaches your user's cookies to it. Without a check, that request is
indistinguishable from a real one.

The defence has two layers here:

1. `SameSite=Lax` on the session cookie, which already stops the browser from
   attaching it to a cross-site POST. This covers most of the attack in every
   current browser.
2. This double-submit check, which does not depend on the browser getting
   SameSite right: a random token is put in a cookie and *also* rendered into
   the form (and into HTMX's headers). A cross-site attacker can make the
   browser send the cookie, but cannot read it to copy it into the form.

**Why the validation is a dependency and not part of the middleware.** Reading
the form inside a middleware consumes the request body, and the handler then
receives nothing — a bug that shows up as "the field is empty" far from its
cause. A dependency runs against the same `Request` object as the endpoint, and
Starlette caches the parsed form, so both see the same data.
"""

from __future__ import annotations

import secrets
from collections.abc import Awaitable, Callable

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.config import Settings
from app.exceptions import CsrfError
from app.security import CSRF_COOKIE_NAME, new_csrf_token, set_csrf_cookie

CSRF_HEADER_NAME = "X-CSRF-Token"
CSRF_FIELD_NAME = "csrf_token"

# Methods that must not change anything, so they need no token.
SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS", "TRACE"})

_FORM_CONTENT_TYPES = ("application/x-www-form-urlencoded", "multipart/form-data")


class CsrfCookieMiddleware(BaseHTTPMiddleware):
    """Make sure every visitor carries a CSRF cookie.

    Only the cookie: the check itself is `csrf_guard` below.
    """

    def __init__(self, app: Callable[..., object], *, settings: Settings) -> None:
        super().__init__(app)  # type: ignore[arg-type]
        self.settings = settings

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        """Put the token on `request.state` and, if it is new, in a cookie."""
        existing = request.cookies.get(CSRF_COOKIE_NAME)
        token = existing or new_csrf_token()
        request.state.csrf_token = token

        response = await call_next(request)

        already_set = any(
            header.startswith(f"{CSRF_COOKIE_NAME}=")
            for header in response.headers.getlist("set-cookie")
        )
        if existing is None and not already_set:
            set_csrf_cookie(response, token, self.settings)

        return response


def csrf_guard(*, enforce: bool = True) -> Callable[[Request], Awaitable[None]]:
    """Build the dependency that rejects requests without a valid token.

    `enforce=False` exists for the test suite, the same way Django's test client
    skips the check by default: every POST in every project's tests would
    otherwise have to fetch a form first. There is deliberately **no environment
    variable** for it — a production deploy must not be one typo away from
    having CSRF protection switched off.
    """

    async def dependency(request: Request) -> None:
        if not enforce or request.method in SAFE_METHODS:
            return

        expected = request.cookies.get(CSRF_COOKIE_NAME, "")
        submitted = request.headers.get(CSRF_HEADER_NAME, "")

        if not submitted and _is_form(request):
            form = await request.form()
            value = form.get(CSRF_FIELD_NAME, "")
            submitted = value if isinstance(value, str) else ""

        # compare_digest, not ==: string comparison stops at the first differing
        # character, and the time it takes leaks how much of the token was right.
        if not expected or not secrets.compare_digest(expected, submitted):
            raise CsrfError

    return dependency


def _is_form(request: Request) -> bool:
    """Whether this request carries a form body worth parsing."""
    content_type = request.headers.get("content-type", "")
    return any(content_type.startswith(kind) for kind in _FORM_CONTENT_TYPES)
