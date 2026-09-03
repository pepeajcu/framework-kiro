"""The contract between the application and whatever actually sends mail.

Kiro never runs its own mail server: reputation, SPF/DKIM/DMARC and blocklists
are a full-time job that no project using this framework wants. Mail leaves
through a third-party API or an existing relay, and this module is the seam
between the two.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class EmailMessage:
    """One outgoing message, already rendered.

    A single recipient by design. This is transactional mail — a password reset,
    a receipt, a notification — which is always addressed to one person. Sending
    the same message to a list is a different problem with different rules
    (unsubscribe headers, batching, suppression lists) and does not belong here.

    Both bodies are required. `text` is not a courtesy: a message with no
    plain-text alternative scores worse with spam filters and shows up empty in
    clients that block HTML.
    """

    to: str
    subject: str
    html: str
    text: str


class EmailSender(Protocol):
    """What the application depends on. Providers satisfy it structurally.

    A Protocol rather than a base class, so an adapter never imports framework
    code and a test double is any object with a matching `send`.
    """

    def send(self, message: EmailMessage) -> None:
        """Deliver the message, or raise `EmailDeliveryError`."""
        ...
