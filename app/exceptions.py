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


class EmailDeliveryError(KiroError):
    """An email could not be handed to the provider.

    Raised by the adapters in `app/emails/providers/`. It means the message did
    not leave — not that it bounced later, which no API reports synchronously.
    """
