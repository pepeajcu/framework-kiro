"""Sends events to GA4 via the Measurement Protocol, server-side.

https://developers.google.com/analytics/devguides/collection/protocol/ga4

The Measurement Protocol has no concept of a session or a browser — every hit
just needs *a* `client_id`. When the caller does not supply one (through
`event.params["client_id"]`, typically read from the client-side `_ga` cookie
by a project that also runs gtag.js), a random one is minted per event. That
event still lands in GA4's reports; it simply cannot be stitched to the same
visitor's other hits. Passing a stable `client_id` is how a project upgrades
that.
"""

from __future__ import annotations

import logging
import uuid

import httpx2

from app.analytics.base import AnalyticsEvent

logger = logging.getLogger(__name__)

ENDPOINT = "https://www.google-analytics.com/mp/collect"


class Ga4AnalyticsSender:
    """`AnalyticsSender` backed by the GA4 Measurement Protocol."""

    def __init__(self, *, measurement_id: str, api_secret: str, timeout: float = 5.0) -> None:
        self._measurement_id = measurement_id
        self._api_secret = api_secret
        self._timeout = timeout

    def track(self, event: AnalyticsEvent) -> None:
        """POST the event. Logs and swallows failures — see ADR-0011."""
        event_params = dict(event.params)
        client_id = event_params.pop("client_id", None) or str(uuid.uuid4())

        try:
            response = httpx2.post(
                ENDPOINT,
                params={
                    "measurement_id": self._measurement_id,
                    "api_secret": self._api_secret,
                },
                json={
                    "client_id": client_id,
                    "events": [{"name": event.name, "params": event_params}],
                },
                timeout=self._timeout,
            )
            response.raise_for_status()
        except httpx2.HTTPError:
            logger.warning("GA4 Measurement Protocol call failed", exc_info=True)
