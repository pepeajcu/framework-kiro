"""What an answer looks like to HTMX.

A full page is the right answer to a navigation and the wrong one to an HTMX
call: swapped into a corner of the page it is already on, a whole 404 document
is worse than saying nothing. This module is the one place that decides which
of the two a request gets, so no handler has to remember to.

- `error_response` — the page for a navigation, a toast for an HTMX call. The
  status code is the same in both.
- `toast_response` — a message and nothing else, for an HTMX call.

The toast is server-rendered markup that HTMX appends to `#toaster` (see
`partials/toast_oob.html`). Basecoat's own JavaScript picks up any `.toast` that
lands there and closes it again after a few seconds, so no script of ours is
involved. Do not use `toaster.toast({...})` from JavaScript for text a visitor
can influence: Basecoat 1.0.2 writes `title` and `description` into the page as
raw HTML, while Jinja escapes them here.

HTMX only swaps a 4xx/5xx response for the status codes listed in the
`htmx-config` tag in `base.html`. Add a code there if you start answering with
a new one.
"""

from __future__ import annotations

from typing import Any, Literal

from fastapi import Request, Response
from fastapi.responses import HTMLResponse

from app.config import Settings
from app.security import FLASH_COOKIE_NAME, FLASH_MAX_AGE_SECONDS, sign_flash
from app.templating import is_htmx, render, templates

ToastCategory = Literal["success", "error", "info", "warning"]


def wants_toast(request: Request) -> bool:
    """Whether the caller is an HTMX call that swaps a fragment into the page.

    A boosted link and a history restore also send `HX-Request`, but they swap
    the whole body: they need a page, not a toast.
    """
    headers = request.headers
    return (
        is_htmx(request)
        and headers.get("HX-Boosted") != "true"
        and headers.get("HX-History-Restore-Request") != "true"
    )


def toast_response(
    request: Request,
    *,
    title: str,
    description: str | None = None,
    category: ToastCategory = "success",
    status_code: int = 200,
    replace_target: bool = False,
) -> HTMLResponse:
    """A response whose effect is a toast.

    By default `HX-Reswap: none` leaves the element that made the request alone and the
    toast travels as an out-of-band swap into `#toaster`. With `replace_target=True` the
    target is replaced by an empty response (it disappears, as in a delete button) and
    the toast still appears.
    """
    headers = {"Vary": "HX-Request"}
    if not replace_target:
        headers["HX-Reswap"] = "none"
    return templates.TemplateResponse(
        request=request,
        name="partials/toast_oob.html",
        context={"category": category, "title": title, "description": description},
        status_code=status_code,
        headers=headers,
    )


def flash(
    response: Response,
    settings: Settings,
    title: str,
    *,
    description: str | None = None,
    category: ToastCategory = "success",
) -> Response:
    """Leave a message for the **next page**: the toast of a post/redirect/get.

    A 303 cannot carry HTML, so the message rides in a short-lived signed cookie that
    `render()` reads, shows once in the toaster and deletes. Returns `response` so it
    reads as `return flash(RedirectResponse("/notes", 303), settings, "Nota guardada")`.
    """
    message = {"category": category, "title": title}
    if description:
        message["description"] = description
    response.set_cookie(
        FLASH_COOKIE_NAME,
        sign_flash(message, settings),
        max_age=FLASH_MAX_AGE_SECONDS,
        httponly=True,
        secure=settings.is_production,
        samesite="lax",
        path="/",
    )
    return response


def error_response(
    request: Request,
    template: str,
    *,
    status_code: int,
    title: str,
    description: str | None = None,
    context: dict[str, Any] | None = None,
) -> HTMLResponse:
    """The page for a navigation, an error toast for an HTMX call."""
    if wants_toast(request):
        return toast_response(
            request,
            title=title,
            description=description,
            category="error",
            status_code=status_code,
        )
    response = render(request, template, context, status_code=status_code)
    # The same URL answers differently to HTMX: a cache must not mix them up.
    response.headers["Vary"] = "HX-Request"
    return response
