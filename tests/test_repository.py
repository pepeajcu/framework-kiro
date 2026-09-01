"""Tests for the generic repository.

`BaseRepository` is what makes the "no SQL outside repositories" rule
enforceable, so its contract is worth pinning down.
"""

from __future__ import annotations

import pytest

from app.repositories.base import BaseRepository


def test_subclass_without_model_fails_at_import_time() -> None:
    """A repository that forgets `model` must fail loudly, and early.

    Catching this when the class is defined means the app refuses to boot,
    instead of raising on whichever endpoint happens to use it first.
    """
    with pytest.raises(TypeError, match="must define a 'model'"):

        class BrokenRepository(BaseRepository):  # type: ignore[type-arg]
            """Deliberately missing the `model` attribute."""
