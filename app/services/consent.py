"""Cookie-consent decision, read from a single cookie.

No consent-management library: the choice is binary (accept marketing cookies
or don't), so a signed session-style token would be overkill. `has_marketing_
consent` is what gates loading GTM in the browser and firing GA4/Meta events on
the server — see ADR-0011.
"""

from __future__ import annotations

CONSENT_COOKIE = "cookie_consent"
CONSENT_COOKIE_MAX_AGE = 365 * 24 * 60 * 60

ACCEPTED = "accepted"
REJECTED = "rejected"


def has_marketing_consent(cookie_value: str | None) -> bool:
    """Whether this visitor accepted the cookie banner.

    Takes the cookie's value rather than the request: a service never sees an
    HTTP object (AGENTS.md), so the router reads `request.cookies` and passes
    the string in.

    Anything other than an explicit "accepted" — no cookie, a rejected one, a
    tampered value — is treated as no. Consent has to be opted into.
    """
    return cookie_value == ACCEPTED
