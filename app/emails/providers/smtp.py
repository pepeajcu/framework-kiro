"""Sends email through an SMTP relay.

For projects that already have a mailbox with their hosting provider, or a
corporate relay. Kiro does not run the server — this talks to someone else's.
"""

from __future__ import annotations

import email.message
import smtplib
import ssl

from app.emails.base import EmailMessage
from app.exceptions import EmailDeliveryError

# Port 465 is implicit TLS: the connection is encrypted from the first byte and
# STARTTLS is not just unnecessary but an error. 587 (and 25) start in the clear
# and upgrade. Getting this backwards is the classic SMTP configuration failure.
IMPLICIT_TLS_PORT = 465


class SmtpEmailSender:
    """`EmailSender` backed by an SMTP server."""

    def __init__(
        self,
        *,
        host: str,
        port: int,
        user: str,
        password: str,
        from_header: str,
        timeout: float = 10.0,
    ) -> None:
        self._host = host
        self._port = port
        self._user = user
        self._password = password
        self._from_header = from_header
        self._timeout = timeout

    def send(self, message: EmailMessage) -> None:
        """Deliver the message, raising `EmailDeliveryError` on failure."""
        payload = self._build(message)
        context = ssl.create_default_context()

        try:
            if self._port == IMPLICIT_TLS_PORT:
                with smtplib.SMTP_SSL(
                    self._host, self._port, timeout=self._timeout, context=context
                ) as server:
                    self._deliver(server, payload)
            else:
                with smtplib.SMTP(self._host, self._port, timeout=self._timeout) as server:
                    server.starttls(context=context)
                    self._deliver(server, payload)
        except (smtplib.SMTPException, OSError) as exc:
            raise EmailDeliveryError(f"SMTP delivery to {self._host} failed: {exc}") from exc

    def _build(self, message: EmailMessage) -> email.message.EmailMessage:
        """Assemble a multipart/alternative message.

        Order matters: `set_content` puts the text part first and
        `add_alternative` appends the HTML one. Clients render the last part
        they understand, so reversing these two sends everyone plain text.
        """
        payload = email.message.EmailMessage()
        payload["From"] = self._from_header
        payload["To"] = message.to
        payload["Subject"] = message.subject
        payload.set_content(message.text)
        payload.add_alternative(message.html, subtype="html")
        return payload

    def _deliver(self, server: smtplib.SMTP, payload: email.message.EmailMessage) -> None:
        """Authenticate if credentials were configured, then send."""
        # An unauthenticated relay is normal on an internal network, so empty
        # credentials are a valid configuration rather than a mistake.
        if self._user:
            server.login(self._user, self._password)
        server.send_message(payload)
