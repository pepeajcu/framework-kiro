"""What a request gets back depends on who is asking: a page or a toast.

An HTMX call that is answered with a whole 404 document would swap that document
into a corner of the page it came from. These tests pin the contract in
`app/hypermedia.py`: same status code, a page for a navigation, a toast for an
HTMX call.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from fastapi import Request
from fastapi.responses import HTMLResponse
from fastapi.testclient import TestClient

from app.hypermedia import toast_response
from app.main import create_app
from app.repositories.note import NoteRepository
from tests.conftest import PASSWORD, override_dependencies

HTMX = {"HX-Request": "true"}
HTMX_CONFIG = re.compile(r"""<meta name="htmx-config" content='(.*?)'>""", re.DOTALL)


def assert_is_a_toast(response, *, status: int, title: str | None = None) -> None:
    assert response.status_code == status
    assert response.headers["HX-Reswap"] == "none"
    assert "HX-Request" in response.headers["Vary"]
    # A fragment, never a document: it is going to be appended to #toaster.
    assert "<html" not in response.text.lower()
    assert 'id="toaster"' in response.text
    assert 'hx-swap-oob="beforeend"' in response.text
    assert 'data-category="error"' in response.text
    if title:
        assert title in response.text


def assert_is_a_page(response, *, status: int) -> None:
    assert response.status_code == status
    assert "HX-Reswap" not in response.headers
    assert "HX-Request" in response.headers["Vary"]
    assert "<html" in response.text.lower()


# --- Errors: page or toast ---------------------------------------------------


def test_a_missing_page_is_a_page_for_a_navigation(client):
    response = client.get("/no-existe")

    assert_is_a_page(response, status=404)
    assert "Esta página no existe" in response.text


def test_a_missing_page_is_a_toast_for_htmx(client):
    response = client.get("/no-existe", headers=HTMX)

    assert_is_a_toast(response, status=404, title="No encontrado")


@pytest.mark.parametrize(
    "headers",
    [
        {"HX-Request": "true", "HX-Boosted": "true"},
        {"HX-Request": "true", "HX-History-Restore-Request": "true"},
    ],
    ids=["boosted-link", "history-restore"],
)
def test_calls_that_swap_the_whole_body_still_get_a_page(client, headers):
    """A boosted link and a history restore send HX-Request, but need a document."""
    response = client.get("/no-existe", headers=headers)

    assert_is_a_page(response, status=404)


def test_a_forbidden_htmx_call_is_a_toast_with_the_same_status(logged_in_client, db_session, auth):
    other = auth.register(email="otra@example.com", password=PASSWORD)
    note = NoteRepository(db_session).create(user_id=other.id, title="Ajena", body="no tocar")
    db_session.flush()

    response = logged_in_client.delete(f"/notes/{note.id}", headers=HTMX)

    assert_is_a_toast(response, status=403, title="Sin permiso")
    assert NoteRepository(db_session).get(note.id) is not None


def test_a_malformed_id_is_a_400_page_not_fastapis_json(logged_in_client):
    response = logged_in_client.delete("/notes/no-es-un-uuid")

    assert_is_a_page(response, status=400)
    assert response.headers["content-type"].startswith("text/html")
    assert "Solicitud no válida" in response.text
    assert "detail" not in response.text


def test_a_malformed_id_is_a_400_toast_for_htmx(logged_in_client):
    response = logged_in_client.delete("/notes/no-es-un-uuid", headers=HTMX)

    assert_is_a_toast(response, status=400, title="Solicitud no válida")


def test_a_form_without_a_csrf_token_is_a_page_or_a_toast(db_session, mailbox):
    """The guard is on here: the `client` fixture turns it off."""
    app = create_app()
    override_dependencies(app, db_session, mailbox)

    with TestClient(app, follow_redirects=False) as strict:
        page = strict.post("/consent", data={"decision": "accepted"})
        toast = strict.post("/consent", data={"decision": "accepted"}, headers=HTMX)

    assert_is_a_page(page, status=403)
    assert "El formulario ha caducado" in page.text
    assert_is_a_toast(toast, status=403, title="El formulario ha caducado")


def test_an_unhandled_error_is_a_500_toast_that_carries_the_reference(db_session, mailbox):
    app = create_app(enforce_csrf=False)
    override_dependencies(app, db_session, mailbox)

    @app.get("/boom")
    def boom() -> None:
        raise RuntimeError("fallo de prueba")

    with TestClient(app, raise_server_exceptions=False) as lenient:
        page = lenient.get("/boom")
        toast = lenient.get("/boom", headers=HTMX)

    assert_is_a_page(page, status=500)
    reference = page.headers["X-Request-ID"]
    assert reference in page.text
    assert_is_a_toast(toast, status=500, title="Algo se rompió por nuestra parte")
    assert f"Referencia: {toast.headers['X-Request-ID']}" in toast.text
    assert reference != toast.headers["X-Request-ID"]


def test_a_method_the_route_does_not_accept_is_a_page_with_allow_not_json(logged_in_client):
    response = logged_in_client.get("/notes/3f6b2c1e-0000-4000-8000-000000000000")

    assert_is_a_page(response, status=405)
    assert response.headers["content-type"].startswith("text/html")
    assert "DELETE" in response.headers["Allow"]
    assert "Acción no permitida" in response.text and "detail" not in response.text


def test_a_method_the_route_does_not_accept_is_a_toast_for_htmx(logged_in_client):
    response = logged_in_client.get("/notes/3f6b2c1e-0000-4000-8000-000000000000", headers=HTMX)

    assert_is_a_toast(response, status=405, title="Acción no permitida")


# --- The toast itself --------------------------------------------------------


def test_the_toast_escapes_what_it_shows(db_session, mailbox):
    """A title can carry user input; Basecoat's own JavaScript API would not escape it."""
    app = create_app(enforce_csrf=False)
    override_dependencies(app, db_session, mailbox)

    @app.get("/aviso")
    def aviso(request: Request) -> HTMLResponse:
        return toast_response(
            request,
            title="<script>alert(1)</script>",
            description='"><img src=x onerror=alert(2)>',
        )

    with TestClient(app) as probe:
        response = probe.get("/aviso", headers=HTMX)

    assert response.status_code == 200
    assert "<script>" not in response.text
    assert "<img" not in response.text
    assert "&lt;script&gt;" in response.text


def test_a_success_toast_is_polite_and_an_error_one_is_an_alert(db_session, mailbox):
    app = create_app(enforce_csrf=False)
    override_dependencies(app, db_session, mailbox)

    @app.get("/ok")
    def ok(request: Request) -> HTMLResponse:
        return toast_response(request, title="Guardado")

    with TestClient(app) as probe:
        response = probe.get("/ok", headers=HTMX)

    assert 'role="status"' in response.text
    assert 'data-category="success"' in response.text


# --- What HTMX does with the answer -----------------------------------------


def _would_swap(config: dict, status: int) -> bool:
    """HTMX's rule: the first entry whose pattern matches the status decides."""
    for entry in config["responseHandling"]:
        if re.search(entry["code"], str(status)):
            return bool(entry["swap"])
    return False


def test_htmx_is_told_to_swap_the_error_codes_the_app_emits(client):
    page = client.get("/")
    match = HTMX_CONFIG.search(page.text)
    assert match is not None, "base.html perdió el <meta name=htmx-config>"
    config = json.loads(match.group(1))

    # Form re-renders (400, 422) and the toasts (403, 404, 500) must be swapped,
    # or the visitor sees nothing happen.
    for status in (200, 303, 400, 403, 404, 405, 409, 422, 429, 500):
        assert _would_swap(config, status), status
    # A 204 means "nothing to show"; a proxy's own error page must stay out.
    for status in (204, 401, 502, 503, 504):
        assert not _would_swap(config, status), status


# --- Rule 10: every page handler declares the viewer -------------------------


@pytest.mark.parametrize(
    ("method", "path", "data"),
    [
        ("get", "/reset-password/no-es-un-token", None),
        ("post", "/reset-password/no-es-un-token", {"password": "x", "password_confirm": "y"}),
        ("post", "/forgot-password", {"email": "no-es-un-email"}),
        ("post", "/login", {"email": "", "password": ""}),
        ("post", "/register", {"email": "", "password": ""}),
    ],
    ids=["reset-form", "reset-post", "forgot-post", "login-post", "register-post"],
)
def test_the_header_knows_who_is_logged_in_on_every_auth_page(
    logged_in_client, user, method, path, data
):
    """Without `OptionalUser` on the handler, the header renders as if nobody were in."""
    response = getattr(logged_in_client, method)(path, **({"data": data} if data else {}))

    assert response.text.count(user.email) >= 1
    assert 'action="/logout"' in response.text


# --- What the server cannot say: network failures, timeouts, a proxy's 502 -------------------


SCRIPT = Path(__file__).resolve().parent.parent / "app/static/js/kiro-htmx.js"


def test_the_page_loads_the_network_error_script_once_and_deferred(client):
    html = client.get("/").text

    assert html.count("js/kiro-htmx.js") == 1
    assert re.search(r'<script src="/static/js/kiro-htmx\.js\?v=\d+" defer></script>', html)


def test_the_script_listens_to_what_htmx_reports_and_cannot_inject_markup():
    """It runs in the browser (checked there, see ADR-0017); here, what must never regress."""
    source = SCRIPT.read_text(encoding="utf-8")
    code = re.sub(r"/\*.*?\*/|//[^\n]*", "", source, flags=re.DOTALL)  # comments are not code

    for event in ("htmx:sendError", "htmx:timeout", "htmx:responseError"):
        assert f'"{event}"' in code
    # The notice is built with textContent: the one innerHTML is its own constant icon.
    assert code.count("innerHTML") == 1 and "content.innerHTML = ERROR_ICON" in code
    assert "textContent = message[0]" in code and "textContent = message[1]" in code
    # It does not double what the server already answered: swapped codes are skipped.
    assert "isSwapped(status)" in code and "responseHandling" in code
    # No dependencies, no inline handlers, no network of its own.
    assert not re.search(
        r"\b(fetch|XMLHttpRequest|eval|document\.write)\b", code.replace("event.detail.xhr", "")
    )


def test_the_messages_are_the_ones_the_docs_promise():
    code = SCRIPT.read_text(encoding="utf-8")

    for message in ("Sin conexión", "La petición tardó demasiado", "El servidor no responde"):
        assert message in code
