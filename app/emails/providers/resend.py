"""Sends email through the Resend HTTP API.

Chosen as the default hosted provider for having an API that is one POST, a
free tier that covers a small project, and no SDK to keep up to date — the call
below is the entire integration.
"""

from __future__ import annotations

import httpx2

from app.emails.base import EmailMessage
from app.exceptions import EmailDeliveryError

ENDPOINT = "https://api.resend.com/emails"


class ResendEmailSender:
    """`EmailSender` backed by Resend."""

    def __init__(self, *, api_key: str, from_header: str, timeout: float = 10.0) -> None:
        self._api_key = api_key
        self._from_header = from_header
        self._timeout = timeout

    def send(self, message: EmailMessage) -> None:
        """POST the message to Resend, raising `EmailDeliveryError` on failure."""
        try:
            response = httpx2.post(
                ENDPOINT,
                headers={"Authorization": f"Bearer {self._api_key}"},
                json={
                    "from": self._from_header,
                    "to": [message.to],
                    "subject": message.subject,
                    "html": message.html,
                    "text": message.text,
                },
                timeout=self._timeout,
            )
            response.raise_for_status()
        except httpx2.HTTPError as exc:
            # The response body carries Resend's own error message ("domain not
            # verified" and friends), which is the part worth reading. Truncated
            # because an HTML error page would otherwise flood the log.
            detail = getattr(getattr(exc, "response", None), "text", "")[:200]
            raise EmailDeliveryError(f"Resend rejected the message: {exc}. {detail}") from exc
