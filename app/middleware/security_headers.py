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
    # googletagmanager.com only matters when GTM_ID is set — see app/config.py.
    # An unused directive here costs nothing; the snippet itself is the gate.
    "script-src": "'self' 'unsafe-inline' https://www.googletagmanager.com",
    # Tailwind ships a stylesheet, but component libraries and the browser's own
    # print styles use inline `style=` attributes.
    "style-src": "'self' 'unsafe-inline'",
    "img-src": "'self' data: https://www.googletagmanager.com",
    "font-src": "'self'",
    # Tags GTM loads (GA4 among them) call these domains directly from the
    # browser, over fetch/beacon — CSP blocks by destination, not by who loaded
    # the script that makes the call.
    "connect-src": (
        "'self' https://www.googletagmanager.com "
        "https://*.google-analytics.com https://*.analytics.google.com"
    ),
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


def apply_security_headers(response: Response, settings: Settings) -> None:
    """Put the headers on a response that has not got them yet.

    `setdefault`, so a route that sets one on purpose keeps its value. Called by
    the middleware for every response the application produces, and by the 500
    handler: Starlette answers an unhandled exception from *outside* the
    middleware stack, so without that second call a server error would be the
    one response with no CSP.
    """
    for header, value in STATIC_HEADERS.items():
        response.headers.setdefault(header, value)
    response.headers.setdefault("Content-Security-Policy", build_csp(CONTENT_SECURITY_POLICY))

    if settings.is_production:
        response.headers.setdefault("Strict-Transport-Security", HSTS)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add the headers to every response the application produces."""

    def __init__(self, app: Callable[..., object], *, settings: Settings) -> None:
        super().__init__(app)  # type: ignore[arg-type]
        self.settings = settings

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        """Attach the headers on the way out."""
        response = await call_next(request)
        apply_security_headers(response, self.settings)
        return response
