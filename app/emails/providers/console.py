"""Prints emails to stdout instead of sending them.

The default provider, and the only safe one for development: no message can
escape the machine. The full text body is printed, links included, so a password
reset can be completed from the terminal without a mail account.
"""

from __future__ import annotations

from app.emails.base import EmailMessage

_RULE = "─" * 72


class ConsoleEmailSender:
    """`EmailSender` that writes to standard output."""

    def send(self, message: EmailMessage) -> None:
        """Print the message. Never fails, never sends."""
        print(f"\n{_RULE}")
        print(f"To:      {message.to}")
        print(f"Subject: {message.subject}")
        print(_RULE)
        print(message.text)
        print(f"{_RULE}\n")
