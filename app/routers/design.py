"""`/_design`: the project's identity on one page. Development only.

Registered in `create_app` only when `settings.design_preview_enabled`, so in a
deployed environment the route does not exist at all (a 404, not a 403).
"""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from app.deps import OptionalUser
from app.services.design import build_page
from app.templating import render

router = APIRouter(include_in_schema=False)


@router.get("/_design", response_class=HTMLResponse)
def design_preview(
    request: Request,
    user: OptionalUser,
    style: str | None = None,
    primary: str | None = None,
    neutral: str | None = None,
    surface: str | None = None,
    secondary: str | None = None,
    radius: str | None = None,
) -> HTMLResponse:
    """Tokens, type scale, components and a test hero, in light and dark.

    `?style=<preset>` and the `[brand]` keys preview a palette without writing
    anything: `?style=brutalista&surface=cream`.
    """
    page = build_page(
        style=style,
        overrides={
            "primary": primary or "",
            "neutral": neutral or "",
            "surface": surface or "",
            "secondary": secondary or "",
            "radius": radius or "",
        },
    )
    status = (
        400
        if page.error and (style or primary or neutral or surface or secondary or radius)
        else 200
    )
    # `consent` fixed so the cookie banner does not cover a page used to judge
    # the design: this is a development tool, it measures nothing.
    return render(
        request, "pages/design.html", {"page": page, "consent": "rejected"}, status_code=status
    )
