"""Server-rendered pages.

Every handler here returns HTML, never JSON. On a normal navigation it returns
a full document; on an HTMX request it may return just the fragment that
changed. Same route, same handler — see `app.templating.is_htmx`.
"""

from __future__ import annotations

import datetime as dt

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from app.templating import render

router = APIRouter(include_in_schema=False)


@router.get("/", response_class=HTMLResponse)
def home(request: Request) -> HTMLResponse:
    """Landing page."""
    return render(request, "pages/home.html")


@router.get("/demo/ping", response_class=HTMLResponse)
def demo_ping(request: Request) -> HTMLResponse:
    """Fragment returned by the HTMX demo on the home page.

    Delete this together with the demo section of `pages/home.html` once the
    project has a real home page.
    """
    return render(
        request,
        "partials/demo_ping.html",
        {"server_time": dt.datetime.now(tz=dt.UTC).strftime("%H:%M:%S UTC")},
    )
