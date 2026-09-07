"""The cookie-consent banner's one endpoint.

HTMX-only: the banner has no non-JS fallback, unlike login. Losing the ability
to accept or reject cookies with JavaScript disabled is an acceptable trade —
GTM would not run anyway without JavaScript, and the default with no decision
made is "no marketing cookies", which is the safe side to fail on.
"""

from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Form, Response
from fastapi.responses import HTMLResponse

from app.services.consent import CONSENT_COOKIE, CONSENT_COOKIE_MAX_AGE

router = APIRouter(tags=["consent"], include_in_schema=False)


@router.post("/consent", response_class=HTMLResponse)
def set_consent(decision: Annotated[Literal["accepted", "rejected"], Form()]) -> Response:
    """Record the visitor's choice and make the banner disappear.

    Empty body with `hx-swap="outerHTML"` on the banner itself: HTMX replaces
    the element with nothing, which removes it from the page without a second
    round trip to re-render anything.
    """
    response = HTMLResponse("")
    response.set_cookie(
        CONSENT_COOKIE,
        decision,
        max_age=CONSENT_COOKIE_MAX_AGE,
        samesite="lax",
        path="/",
    )
    return response
