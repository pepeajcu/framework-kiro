"""Private notes — Kiro's worked example of the golden path.

Everything the `kiro-feature` skill describes in prose, running: a model, a
migration, a repository, a schema, a service with a real rule to enforce, a
router, templates, and tests. Read this before asking an agent for your first
real feature — it is easier to copy a pattern from working code than from a
snippet.

**Safe to delete wholesale** if a project does not want it. The full set:

- `app/models/note.py` (and its import in `app/models/__init__.py`)
- the migration that creates `notes` (`make revision` finds it by table name)
- `app/repositories/note.py`
- `app/schemas/note.py`
- `app/services/note.py`
- `app/routers/notes.py` (this file, and its registration in `app/main.py`)
- `app/templates/pages/notes/`
- the "Notas" link in `app/templates/partials/header.html`
- `tests/test_notes.py`

Two request/response patterns on purpose, one per route:

- Creating a note is a **plain form** — POST/redirect/GET, no HTMX, no
  JavaScript required. `app/routers/auth.py` is the other worked example of
  this pattern.
- Deleting one is **pure HTMX** — `hx-delete`, an empty response, and
  `hx-swap="outerHTML"` removing the note's own element. The same pattern as
  `partials/cookie_consent.html`.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Form, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import ValidationError

from app.deps import CurrentUser, DbSession
from app.repositories.note import NoteRepository
from app.schemas import form_errors
from app.schemas.note import NoteCreate
from app.services.note import NoteService
from app.templating import render

router = APIRouter(tags=["notes"], include_in_schema=False)

SEE_OTHER = 303


@router.get("/notes", response_class=HTMLResponse)
def list_notes(request: Request, db: DbSession, user: CurrentUser) -> HTMLResponse:
    """A logged-in account's own notes, plus the form to add one."""
    notes = NoteRepository(db).list_for_user(user.id)
    return render(request, "pages/notes/index.html", {"notes": notes})


@router.post("/notes", response_class=HTMLResponse)
def create_note(
    request: Request,
    db: DbSession,
    user: CurrentUser,
    title: Annotated[str, Form()] = "",
    body: Annotated[str, Form()] = "",
) -> Response:
    """Add a note. Plain post/redirect/get — this route needs no JavaScript."""
    try:
        form = NoteCreate(title=title, body=body)
    except ValidationError as exc:
        notes = NoteRepository(db).list_for_user(user.id)
        return render(
            request,
            "pages/notes/index.html",
            {"notes": notes, "errors": form_errors(exc), "title": title, "body": body},
            status_code=400,
        )

    NoteService(db).create_for_user(user, title=form.title, body=form.body)
    return RedirectResponse("/notes", status_code=SEE_OTHER)


@router.delete("/notes/{note_id}", response_class=HTMLResponse)
def delete_note(db: DbSession, user: CurrentUser, note_id: uuid.UUID) -> HTMLResponse:
    """Delete one of the account's own notes.

    HTMX-only: the button that calls this sends `hx-delete` and swaps its own
    `<article>` for this empty response, which removes it from the page.
    """
    NoteService(db).delete_owned(user, note_id)
    return HTMLResponse("")
