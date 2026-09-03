"""Domain exceptions.

These are deliberately framework-free: the repository and service layers raise
them without importing FastAPI, and `app.main` maps them to HTTP responses.
That keeps business logic testable without spinning up an app.
"""

from __future__ import annotations


class KiroError(Exception):
    """Base class for every error this application raises on purpose."""


class NotFoundError(KiroError):
    """A requested entity does not exist."""

    def __init__(self, entity: str, identifier: object) -> None:
        self.entity = entity
        self.identifier = identifier
        super().__init__(f"{entity} not found: {identifier!r}")


class ConflictError(KiroError):
    """The operation clashes with existing state (duplicate, version mismatch)."""


class PermissionDeniedError(KiroError):
    """The current user may not perform this action."""


class AuthenticationRequiredError(KiroError):
    """Nobody is logged in and the page needs somebody to be.

    Not an error the user caused, which is why `app.main` turns it into a
    redirect to the login form rather than an error page.
    """

    def __init__(self, next_url: str = "/") -> None:
        self.next_url = next_url
        super().__init__("authentication required")


class InvalidCredentialsError(KiroError):
    """The email or the password is wrong, or the account is disabled.

    Deliberately one exception for all three. Telling a stranger which of them
    it was hands them a way to find out who has an account here.
    """


class CsrfError(KiroError):
    """A state-changing request arrived without a matching CSRF token.

    Usually not an attack: a form left open long enough for its token to expire
    produces exactly this. The page it renders says so, instead of accusing the
    visitor of something.
    """


class InvalidTokenError(KiroError):
    """A signed or single-use token is unknown, expired or already spent."""


class EmailDeliveryError(KiroError):
    """An email could not be handed to the provider.

    Raised by the adapters in `app/emails/providers/`. It means the message did
    not leave — not that it bounced later, which no API reports synchronously.
    """
