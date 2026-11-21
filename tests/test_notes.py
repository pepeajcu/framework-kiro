"""Tests for the notes example — the framework's worked golden path.

Covers what the example is meant to demonstrate: the plain-form create path,
the HTMX delete path, and the one real business rule (only the owner can
delete a note).
"""

from __future__ import annotations

import shutil
from pathlib import Path

from scripts.archcheck import check_project
from scripts.strip_example import strip_example

from app.repositories.note import NoteRepository
from tests.conftest import PROJECT_ROOT


def test_anonymous_visitor_is_sent_to_login(client):
    response = client.get("/notes")

    assert response.status_code == 303
    assert response.headers["location"].startswith("/login")


def test_the_notes_page_uses_the_empty_state(logged_in_client):
    page = logged_in_client.get("/notes").text

    assert "Aún no tienes notas" in page and "border-dashed" in page


def test_creating_a_note_redirects_and_lists_it(logged_in_client):
    response = logged_in_client.post("/notes", data={"title": "Compras", "body": "Leche, pan"})

    assert response.status_code == 303
    assert response.headers["location"] == "/notes"

    page = logged_in_client.get("/notes")
    assert "Compras" in page.text
    assert "Leche, pan" in page.text
    assert "Nota guardada" in page.text


def test_an_empty_title_fails_validation_with_400_and_keeps_body(logged_in_client):
    response = logged_in_client.post("/notes", data={"title": "", "body": "Lo que escribí"})

    assert response.status_code == 400
    assert "<textarea" in response.text and "Lo que escribí" in response.text


def test_deleting_a_note_removes_it(logged_in_client, db_session, user):
    note = NoteRepository(db_session).create(user_id=user.id, title="Temporal", body="borrar")
    db_session.flush()

    response = logged_in_client.delete(f"/notes/{note.id}")

    assert response.status_code == 200
    # The note's element is replaced by nothing, and a toast says what happened.
    assert "HX-Reswap" not in response.headers
    assert "Nota eliminada" in response.text and 'hx-swap-oob="beforeend"' in response.text
    assert NoteRepository(db_session).get(note.id) is None


def test_cannot_delete_someone_elses_note(logged_in_client, db_session, auth):
    other = auth.register(email="otra@example.com", password="una contraseña larga de prueba")
    note = NoteRepository(db_session).create(user_id=other.id, title="Ajena", body="no tocar")
    db_session.flush()

    response = logged_in_client.delete(f"/notes/{note.id}")

    assert response.status_code == 403
    assert NoteRepository(db_session).get(note.id) is not None


def test_strip_example_removes_notes_cleanly_and_passes_archcheck(tmp_path: Path):
    shutil.copytree(PROJECT_ROOT / "app", tmp_path / "app")
    shutil.copytree(PROJECT_ROOT / "migrations", tmp_path / "migrations")
    (tmp_path / "tests").mkdir()
    shutil.copy2(PROJECT_ROOT / "tests" / "test_notes.py", tmp_path / "tests" / "test_notes.py")

    removed = strip_example(tmp_path)

    assert "app/routers/notes.py" in removed
    assert not (tmp_path / "app" / "models" / "note.py").exists()
    assert not (tmp_path / "app" / "routers" / "notes.py").exists()
    assert not (tmp_path / "app" / "templates" / "pages" / "notes").exists()
    assert not (tmp_path / "tests" / "test_notes.py").exists()
    assert "notes" not in (tmp_path / "app" / "main.py").read_text(encoding="utf-8")
    assert "/notes" not in (
        tmp_path / "app" / "templates" / "partials" / "nav_auth.html"
    ).read_text(encoding="utf-8")
    assert check_project(tmp_path).ok
    # Idempotent on a second run.
    assert strip_example(tmp_path) == []
