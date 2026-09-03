"""Building the configured email sender.

One place decides which adapter the application uses, driven by
`EMAIL_PROVIDER`. Nothing else in the codebase names a provider — services
depend on the `EmailSender` protocol, so swapping Resend for SMTP is an
environment variable, not a code change.
"""

from __future__ import annotations

from functools import lru_cache

from app.config import EmailProvider, get_settings
from app.emails.base import EmailSender
from app.emails.providers.console import ConsoleEmailSender
from app.emails.providers.resend import ResendEmailSender
from app.emails.providers.smtp import SmtpEmailSender


@lru_cache(maxsize=1)
def get_email_sender() -> EmailSender:
    """Return the process-wide sender for the configured provider.

    Also a FastAPI dependency: inject `Emailer` from `app.deps` in a route, and
    a test can replace it through `app.dependency_overrides`.
    """
    settings = get_settings()

    match settings.email_provider:
        case EmailProvider.CONSOLE:
            return ConsoleEmailSender()
        case EmailProvider.RESEND:
            return ResendEmailSender(
                api_key=settings.resend_api_key,
                from_header=settings.email_from_header,
            )
        case EmailProvider.SMTP:
            return SmtpEmailSender(
                host=settings.smtp_host,
                port=settings.smtp_port,
                user=settings.smtp_user,
                password=settings.smtp_password,
                from_header=settings.email_from_header,
            )
