"""Note input schema.

Part of the worked example — see `app/routers/notes.py`.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class NoteCreate(BaseModel):
    """Payload accepted by the note creation form."""

    title: str = Field(min_length=1, max_length=120)
    body: str = Field(min_length=1, max_length=4000)
