"""Sends events to Meta's Conversions API, server-side.

https://developers.facebook.com/docs/marketing-api/conversions-api

`user_data` carries only hashed contact fields (`sha256_lower`, never the raw
value) plus the IP and user agent, which Meta uses unhashed to help match the
event to a browsing session. `action_source: "website"` tells Meta this event
mirrors something that happened in a browser, even though it was sent from a
server.
"""

from __future__ import annotations

import logging
import time

import httpx2

from app.analytics.base import AnalyticsEvent
from app.analytics.hashing import sha256_lower

logger = logging.getLogger(__name__)

API_VERSION = "v21.0"


class MetaAnalyticsSender:
    """`AnalyticsSender` backed by the Meta Conversions API."""

    def __init__(self, *, pixel_id: str, access_token: str, timeout: float = 5.0) -> None:
        self._pixel_id = pixel_id
        self._access_token = access_token
        self._timeout = timeout

    def track(self, event: AnalyticsEvent) -> None:
        """POST the event. Logs and swallows failures — see ADR-0011."""
        user_data: dict[str, str] = {}
        if event.email:
            user_data["em"] = sha256_lower(event.email)
        if event.ip_address:
            user_data["client_ip_address"] = event.ip_address
        if event.user_agent:
            user_data["client_user_agent"] = event.user_agent

        payload = {
            "data": [
                {
                    "event_name": event.name,
                    "event_time": int(time.time()),
                    "action_source": "website",
                    "user_data": user_data,
                    "custom_data": event.params,
                }
            ]
        }

        try:
            response = httpx2.post(
                f"https://graph.facebook.com/{API_VERSION}/{self._pixel_id}/events",
                params={"access_token": self._access_token},
                json=payload,
                timeout=self._timeout,
            )
            response.raise_for_status()
        except httpx2.HTTPError:
            logger.warning("Meta Conversions API call failed", exc_info=True)
