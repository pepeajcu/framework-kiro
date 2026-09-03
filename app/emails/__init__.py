"""Transactional email.

    from app.emails import render_email
    from app.deps import Emailer

    def notify(emailer: Emailer) -> None:
        emailer.send(render_email("password_reset", to=user.email, reset_url=url))

`app/templates/emails/` holds the wording; this package holds the plumbing.
Which provider actually delivers is decided by `EMAIL_PROVIDER` — see
`sender.py`.
"""

from app.emails.base import EmailMessage, EmailSender
from app.emails.providers.memory import MemoryEmailSender
from app.emails.render import render_email
from app.emails.sender import get_email_sender

__all__ = [
    "EmailMessage",
    "EmailSender",
    "MemoryEmailSender",
    "get_email_sender",
    "render_email",
]
