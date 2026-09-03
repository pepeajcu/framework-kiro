"""Keeps emails in a list instead of sending them. For tests.

Deliberately **not** selectable through `EMAIL_PROVIDER`: a deployment that
picked it by accident would swallow every password reset in silence. Import it
in a test and override the `get_email_sender` dependency:

    sender = MemoryEmailSender()
    app.dependency_overrides[get_email_sender] = lambda: sender
    ...
    assert "reset" in sender.last.text
"""

from __future__ import annotations

from app.emails.base import EmailMessage


class MemoryEmailSender:
    """`EmailSender` that records messages instead of delivering them."""

    def __init__(self) -> None:
        self.outbox: list[EmailMessage] = []

    def send(self, message: EmailMessage) -> None:
        """Record the message."""
        self.outbox.append(message)

    @property
    def last(self) -> EmailMessage:
        """The most recent message, or raise if nothing was sent.

        Raising beats returning None: a test that asserts on the wrong thing
        should say "no email was sent", not "NoneType has no attribute".
        """
        if not self.outbox:
            raise AssertionError("no email was sent")
        return self.outbox[-1]

    def clear(self) -> None:
        """Empty the outbox."""
        self.outbox.clear()
