"""Jinja2 configuration.

One configured `templates` object for the whole application. Import it instead
of building `Jinja2Templates` per router, so the globals registered here are
available on every page.
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path
from typing import Any

from fastapi import Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.config import get_settings

TEMPLATES_DIR = Path(__file__).parent / "templates"
STATIC_DIR = Path(__file__).parent / "static"

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


def asset(path: str) -> str:
    """Build a URL for a static file, cache-busted by its modification time.

    Static assets are served with long cache headers, so a deploy that changes
    `app.css` would otherwise leave visitors on the old stylesheet until they
    hard-refresh. The `?v=` suffix changes with the file, forcing a re-fetch
    only when there is something new to fetch.
    """
    url = f"/static/{path.lstrip('/')}"
    file_path = STATIC_DIR / path.lstrip("/")
    try:
        return f"{url}?v={int(file_path.stat().st_mtime)}"
    except OSError:
        # The file does not exist yet (CSS not built, or a typo). Returning the
        # plain URL keeps the page rendering; the browser's 404 makes it obvious.
        return url


def now_year() -> int:
    """Current year, for copyright notices.

    A callable rather than a constant: a process that stays up across New Year
    would otherwise keep rendering the old year.
    """
    return dt.datetime.now(tz=dt.UTC).year


templates.env.globals["settings"] = get_settings()
templates.env.globals["asset"] = asset
templates.env.globals["now_year"] = now_year


def is_htmx(request: Request) -> bool:
    """Whether this request came from HTMX rather than a full page load.

    HTMX sets `HX-Request: true` on every request it issues. Use it to return a
    fragment instead of a whole page — same URL, same handler, two renderings.
    """
    return request.headers.get("HX-Request") == "true"


def render(
    request: Request,
    template: str,
    context: dict[str, Any] | None = None,
    *,
    status_code: int = 200,
) -> HTMLResponse:
    """Render a template into an HTML response.

    Thin wrapper over Starlette's `TemplateResponse` that keeps `request` out of
    every call site's context dict.

    `user` and `csrf_token` are added automatically from `request.state`,
    where the authentication dependencies and the CSRF middleware leave them, so
    no handler has to pass them. `user` is None on pages whose handler does not
    declare `OptionalUser` or `CurrentUser`.
    """
    merged = dict(context or {})
    merged.setdefault("user", getattr(request.state, "user", None))
    # Left there by CsrfCookieMiddleware. Every form needs it, so no template
    # should have to be passed it by hand.
    merged.setdefault("csrf_token", getattr(request.state, "csrf_token", ""))

    return templates.TemplateResponse(
        request=request,
        name=template,
        context=merged,
        status_code=status_code,
    )
