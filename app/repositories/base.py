"""Generic, fully typed repository.

Subclass it per model to get the common CRUD operations for free:

    class ProviderRepository(BaseRepository[Provider]):
        model = Provider

        def find_active_by_city(self, city: str) -> Sequence[Provider]:
            stmt = select(Provider).where(
                Provider.city == city,
                Provider.subscription_active.is_(True),
            )
            return self.session.scalars(stmt).all()

Project-specific queries go in the subclass, as methods with meaningful names —
never inline in a router.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.exceptions import NotFoundError
from app.models.base import Base


class BaseRepository[ModelT: Base]:
    """CRUD operations shared by every model."""

    model: type[ModelT]

    def __init__(self, session: Session) -> None:
        self.session = session

    def __init_subclass__(cls, **kwargs: Any) -> None:
        """Fail at import time if a subclass forgets to declare `model`.

        Catching this on import rather than on first query means a typo shows up
        when the app boots, not when a user hits the one endpoint that uses it.
        """
        super().__init_subclass__(**kwargs)
        if not hasattr(cls, "model"):
            raise TypeError(f"{cls.__name__} must define a 'model' class attribute")

    # --- Reads -------------------------------------------------------------

    def get(self, entity_id: Any) -> ModelT | None:
        """Return the entity with this primary key, or None."""
        return self.session.get(self.model, entity_id)

    def get_or_raise(self, entity_id: Any) -> ModelT:
        """Return the entity, or raise `NotFoundError`.

        Prefer this in routes: it removes the `if obj is None` branch from every
        handler and produces one consistent 404.
        """
        instance = self.get(entity_id)
        if instance is None:
            raise NotFoundError(self.model.__name__, entity_id)
        return instance

    def list(self, *, limit: int = 50, offset: int = 0) -> Sequence[ModelT]:
        """Return a page of entities.

        `limit` defaults to 50 on purpose: an unbounded list is a page that
        works in development and falls over in production.
        """
        stmt = select(self.model).limit(limit).offset(offset)
        return self.session.scalars(stmt).all()

    def count(self) -> int:
        """Total number of rows."""
        stmt = select(func.count()).select_from(self.model)
        return self.session.scalar(stmt) or 0

    def exists(self, entity_id: Any) -> bool:
        """Whether a row with this primary key exists, without loading it."""
        return self.get(entity_id) is not None

    # --- Writes ------------------------------------------------------------
    #
    # None of these commit. The transaction is owned by the request (see
    # `app.db.get_db`), so a later failure rolls back the whole unit of work
    # instead of leaving half of it persisted.

    def create(self, **values: Any) -> ModelT:
        """Add a new entity to the session and flush to get its generated id."""
        instance = self.model(**values)
        self.session.add(instance)
        self.session.flush()
        return instance

    def update(self, instance: ModelT, **values: Any) -> ModelT:
        """Apply field updates to an entity already in the session."""
        for field, value in values.items():
            if not hasattr(instance, field):
                raise AttributeError(f"{self.model.__name__} has no field {field!r}")
            setattr(instance, field, value)
        self.session.flush()
        return instance

    def delete(self, instance: ModelT) -> None:
        """Remove an entity."""
        self.session.delete(instance)
        self.session.flush()
