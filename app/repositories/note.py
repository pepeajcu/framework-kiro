"""Note data access.

Part of the worked example — see `app/routers/notes.py`.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy import select

from app.models.note import Note
from app.repositories.base import BaseRepository


class NoteRepository(BaseRepository[Note]):
    """Queries over notes."""

    model = Note

    def list_for_user(self, user_id: uuid.UUID) -> Sequence[Note]:
        """A user's notes, newest first."""
        stmt = select(Note).where(Note.user_id == user_id).order_by(Note.created_at.desc())
        return self.session.scalars(stmt).all()
