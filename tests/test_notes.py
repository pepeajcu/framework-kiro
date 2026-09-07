"""Tests for the notes example — the framework's worked golden path.

Covers what the example is meant to demonstrate: the plain-form create path,
the HTMX delete path, and the one real business rule (only the owner can
delete a note).
"""

from __future__ import annotations

from app.repositories.note import NoteRepository


def test_anonymous_visitor_is_sent_to_login(client):
    response = client.get("/notes")

    assert response.status_code == 303
    assert response.headers["location"].startswith("/login")


def test_creating_a_note_redirects_and_lists_it(logged_in_client):
    response = logged_in_client.post("/notes", data={"title": "Compras", "body": "Leche, pan"})

    assert response.status_code == 303
    assert response.headers["location"] == "/notes"

    page = logged_in_client.get("/notes")
    assert "Compras" in page.text
    assert "Leche, pan" in page.text


def test_an_empty_title_fails_validation_with_400(logged_in_client):
    response = logged_in_client.post("/notes", data={"title": "", "body": "algo"})

    assert response.status_code == 400


def test_deleting_a_note_removes_it(logged_in_client, db_session, user):
    note = NoteRepository(db_session).create(user_id=user.id, title="Temporal", body="borrar")
    db_session.flush()

    response = logged_in_client.delete(f"/notes/{note.id}")

    assert response.status_code == 200
    assert response.text == ""
    assert NoteRepository(db_session).get(note.id) is None


def test_cannot_delete_someone_elses_note(logged_in_client, db_session, auth):
    other = auth.register(email="otra@example.com", password="una contraseña larga de prueba")
    note = NoteRepository(db_session).create(user_id=other.id, title="Ajena", body="no tocar")
    db_session.flush()

    response = logged_in_client.delete(f"/notes/{note.id}")

    assert response.status_code == 403
    assert NoteRepository(db_session).get(note.id) is not None
