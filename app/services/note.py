"""Note business logic.

Part of the worked example — see `app/routers/notes.py`. The one rule that
justifies this layer (a plain-CRUD feature would not need it): a note can only
be deleted by the account that wrote it.
"""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.exceptions import PermissionDeniedError
from app.models.note import Note
from app.models.user import User
from app.repositories.note import NoteRepository


class NoteService:
    """Creating and deleting notes, with ownership enforced."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.notes = NoteRepository(db)

    def create_for_user(self, user: User, *, title: str, body: str) -> Note:
        """Add a note owned by `user`."""
        return self.notes.create(user_id=user.id, title=title, body=body)

    def delete_owned(self, user: User, note_id: uuid.UUID) -> None:
        """Delete a note, or raise if it belongs to someone else.

        `get_or_raise` turns a missing id into `NotFoundError` (a 404); a
        mismatched owner is `PermissionDeniedError` (a 403) — deliberately
        different from "not found", the same distinction `require_role` makes
        in `app/deps.py`.
        """
        note = self.notes.get_or_raise(note_id)
        if note.user_id != user.id:
            raise PermissionDeniedError("note belongs to another account")
        self.notes.delete(note)
