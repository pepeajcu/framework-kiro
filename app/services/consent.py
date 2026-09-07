"""Cookie-consent decision, read from a single cookie.

No consent-management library: the choice is binary (accept marketing cookies
or don't), so a signed session-style token would be overkill. `has_marketing_
consent` is what gates loading GTM in the browser and firing GA4/Meta events on
the server — see ADR-0011.
"""

from __future__ import annotations

from fastapi import Request

CONSENT_COOKIE = "cookie_consent"
CONSENT_COOKIE_MAX_AGE = 365 * 24 * 60 * 60

ACCEPTED = "accepted"
REJECTED = "rejected"


def has_marketing_consent(request: Request) -> bool:
    """Whether this visitor accepted the cookie banner.

    Anything other than an explicit "accepted" — no cookie, a rejected one, a
    tampered value — is treated as no. Consent has to be opted into.
    """
    return request.cookies.get(CONSENT_COOKIE) == ACCEPTED
