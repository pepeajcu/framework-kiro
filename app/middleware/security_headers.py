"""Security headers on every response.

Each header here closes one attack that needs no bug in the application to work:
clickjacking, MIME sniffing, a form posting somewhere else, a page framed inside
somebody's phishing site.

Edit `CONTENT_SECURITY_POLICY` below to fit your project. It is a plain dict on
purpose: a CSP written as one long string is a CSP nobody dares to change.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.config import Settings

# The Content-Security-Policy, directive by directive.
#
# **About `'unsafe-inline'` in script-src.** It is not there by choice. Nine
# Basecoat components ship inline `onclick` handlers (dialog, command, toast),
# and a CSP without `'unsafe-inline'` silently refuses to run them — the dialog
# simply never opens. Those files are vendored and get overwritten on update, so
# patching them is not an option.
#
# What it costs: an injected `<script>` in a page would execute. What still
# holds without it: `default-src 'self'` blocks loading scripts from anywhere
# else, `form-action 'self'` stops a form being posted to another site,
# `frame-ancestors 'none'` stops the page being framed, and `base-uri 'self'`
# stops a `<base>` tag rewriting every relative URL on the page.
#
# To tighten it: if your project does not use the dialog, command or toast
# macros, drop `'unsafe-inline'` from script-src and check the console. See
# ADR-0010.
CONTENT_SECURITY_POLICY = {
    "default-src": "'self'",
    "script-src": "'self' 'unsafe-inline'",
    # Tailwind ships a stylesheet, but component libraries and the browser's own
    # print styles use inline `style=` attributes.
    "style-src": "'self' 'unsafe-inline'",
    "img-src": "'self' data:",
    "font-src": "'self'",
    "connect-src": "'self'",
    "form-action": "'self'",
    "frame-ancestors": "'none'",
    "base-uri": "'self'",
    "object-src": "'none'",
}

STATIC_HEADERS = {
    # Stops the browser from guessing a content type — the trick that turns an
    # uploaded "image" into an executed script.
    "X-Content-Type-Options": "nosniff",
    # Belt and braces with frame-ancestors, for browsers that predate CSP.
    "X-Frame-Options": "DENY",
    # Full URL to our own pages, only the origin to other sites: a reset link in
    # the address bar never leaks its token through a Referer header.
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
}

# One year. Only sent in a deployed environment: promising a browser that this
# host is HTTPS-only, from a laptop serving plain HTTP on localhost, locks you
# out of your own development server until you clear the browser's HSTS list.
#
# `preload` is deliberately absent. It is close to irreversible: getting a
# domain off the preload list takes months and a browser release.
HSTS = "max-age=31536000; includeSubDomains"


def build_csp(directives: dict[str, str]) -> str:
    """Render the policy dict into a header value."""
    return "; ".join(f"{name} {value}" for name, value in directives.items())


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add the headers to every response the application produces."""

    def __init__(self, app: Callable[..., object], *, settings: Settings) -> None:
        super().__init__(app)  # type: ignore[arg-type]
        self.settings = settings
        self.csp = build_csp(CONTENT_SECURITY_POLICY)

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        """Attach the headers on the way out."""
        response = await call_next(request)

        for header, value in STATIC_HEADERS.items():
            response.headers.setdefault(header, value)
        response.headers.setdefault("Content-Security-Policy", self.csp)

        if self.settings.is_production:
            response.headers.setdefault("Strict-Transport-Security", HSTS)

        return response
