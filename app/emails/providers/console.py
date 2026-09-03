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
        """Print the message. Never fails, never sends.

        `flush=True` is not cosmetic. Python block-buffers stdout when it is not
        a terminal — which is exactly the case under `make dev > log`, under a
        process manager, or in any container without PYTHONUNBUFFERED. Without
        the flush, the reset link you are waiting for sits in a buffer, and the
        default email provider appears to do nothing at all.
        """
        print(
            f"\n{_RULE}\n"
            f"To:      {message.to}\n"
            f"Subject: {message.subject}\n"
            f"{_RULE}\n"
            f"{message.text}\n"
            f"{_RULE}\n",
            flush=True,
        )
