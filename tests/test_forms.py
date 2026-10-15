"""Forms with memory, and messages that survive a redirect.

`validate_form` returns the model or a result that carries what was typed and the errors;
the macros read it, so a rejected form is the same page again with nothing copied by hand.
A flash is the toast of a post/redirect/get: a signed cookie, shown once, then deleted.
"""

from __future__ import annotations

import re

import pytest
from fastapi import Request, Response
from fastapi.responses import RedirectResponse
from fastapi.testclient import TestClient
from pydantic import BaseModel, Field

from app.config import get_settings
from app.hypermedia import flash
from app.main import create_app
from app.repositories.note import NoteRepository
from app.schemas import FormResult, validate_form
from app.schemas.auth import LoginForm
from app.security import FLASH_COOKIE_NAME, sign_flash, unsign_flash
from app.templating import render, templates
from tests.conftest import PASSWORD, override_dependencies

HOSTILE = '"><script>alert(1)</script>'


class Signup(BaseModel):
    name: str = Field(min_length=2)
    password: str = Field(min_length=8)
    age: int


# --- validate_form --------


def test_a_valid_form_gives_the_model_and_no_errors() -> None:
    result = validate_form(Signup, name="Ana", password="una-contraseña", age="31")

    assert result.ok and result.data == Signup(name="Ana", password="una-contraseña", age=31)
    assert result.errors == {}


def test_an_invalid_form_keeps_what_was_typed_and_the_first_error_per_field() -> None:
    result = validate_form(Signup, name="A", password="corta", age="treinta")

    assert not result.ok and result.data is None
    assert set(result.errors) == {"name", "password", "age"}
    assert result.values == {"name": "A", "age": "treinta"}


@pytest.mark.parametrize("field_name", ["password", "new_password", "client_secret", "csrf_token"])
def test_secrets_never_come_back_to_the_browser(field_name: str) -> None:
    class Model(BaseModel):
        email: str

    result = validate_form(Model, **{"email": "a@b.c", field_name: "no-me-devuelvas"})  # type: ignore[arg-type]

    assert result.values == {"email": "a@b.c", field_name: "no-me-devuelvas"}.keys() & {
        "email"
    } or (field_name not in result.values and result.values["email"] == "a@b.c")
    assert field_name not in result.values


def test_validate_form_never_raises_even_on_missing_or_hostile_input() -> None:
    assert not validate_form(Signup).ok
    assert not validate_form(Signup, name=HOSTILE * 100, password="x", age="1e999").ok


def test_an_extra_complaint_keeps_the_input_and_cancels_success() -> None:
    ok = validate_form(LoginForm, email="ana@example.com", password=PASSWORD)

    refused = ok.with_errors({"__all__": "Email o contraseña incorrectos"})

    assert ok.ok and not refused.ok
    assert refused.values == {"email": "ana@example.com"}
    assert refused.errors == {"__all__": "Email o contraseña incorrectos"}
    assert isinstance(refused, FormResult)


# --- The macros --------

IMPORT = (
    '{% from "components/form.html.jinja" import field, textarea, select, checkbox, form_error %}'
)


def page(source: str, form: object = None) -> str:
    return templates.env.from_string(IMPORT + source).render(form=form)


def failed(**raw: str) -> FormResult[Signup]:
    return validate_form(Signup, **{"name": "A", "password": "x", "age": "1", **raw})


def test_a_field_shows_what_was_typed_and_its_error_and_links_them_for_screen_readers() -> None:
    html = page('{{ field("name", "Nombre", form=form, help="Como en tu DNI") }}', failed(name="A"))

    assert 'value="A"' in html
    assert 'aria-invalid="true"' in html
    assert 'aria-describedby="name-error name-help"' in html
    assert 'id="name-error"' in html and 'id="name-help"' in html
    assert 'data-invalid="true"' in html


def test_a_field_without_a_form_or_an_error_is_plain() -> None:
    html = page('{{ field("name", "Nombre", form=form) }}')

    assert 'value=""' in html and "aria-invalid" not in html and "aria-describedby" not in html


def test_the_old_value_and_errors_arguments_still_work() -> None:
    html = page('{{ field("name", "Nombre", value="Ana", errors={"name": "Muy corto"}) }}')

    assert 'value="Ana"' in html and "Muy corto" in html


def test_a_password_field_is_never_filled_in() -> None:
    form = validate_form(Signup, name="Ana", password="secreta-secreta", age="x")

    html = page('{{ field("password", "Contraseña", type="password", form=form) }}', form)
    # Even if a handler put it in `values` by hand, a password input is rendered empty.
    forced = FormResult(values={"password": "secreta"})
    forced_html = page('{{ field("password", "C", type="password", form=form) }}', forced)

    assert 'value=""' in html and "secreta" not in html
    assert 'value=""' in forced_html and "secreta" not in forced_html


def test_a_textarea_is_filled_with_the_escaped_text() -> None:
    form = FormResult(values={"body": HOSTILE + "\nsegunda línea"})

    html = page('{{ textarea("body", "Contenido", form=form, rows=3) }}', form)

    assert "<script>" not in html and "&lt;script&gt;" in html
    assert "segunda línea" in html and 'rows="3"' in html and "</textarea>" in html


def test_a_select_marks_the_chosen_option_and_escapes_the_rest() -> None:
    form = FormResult(values={"pais": "mx"})
    options = '[{"value": "es", "label": "España"}, {"value": "mx", "label": "México"}]'

    html = page(
        '{{ select("pais", "País", ' + options + ', form=form, placeholder="Elige") }}', form
    )

    assert re.search(r'value="mx"\s+selected', html) and not re.search(
        r'value="es"\s+selected', html
    )
    assert "Elige" in html


def test_a_select_does_not_trust_option_labels() -> None:
    html = templates.env.from_string(
        IMPORT + '{{ select("x", "X", [{"value": v, "label": v}]) }}'
    ).render(v=HOSTILE)

    assert "<script>" not in html and "&lt;script&gt;" in html


def test_a_checkbox_is_checked_when_it_was_sent_and_unchecked_when_it_was_not() -> None:
    sent = page(
        '{{ checkbox("acepto", "Acepto", form=form) }}', FormResult(values={"acepto": "on"})
    )
    absent = page('{{ checkbox("acepto", "Acepto", form=form) }}', FormResult(values={"otro": "x"}))
    default = page('{{ checkbox("acepto", "Acepto", checked=True, form=form) }}')

    assert "checked" in sent and "checked" not in absent and "checked" in default


def test_the_general_error_of_a_form_is_shown_once_and_only_when_there_is_one() -> None:
    refused = validate_form(LoginForm, email="a@b.co", password="x").with_errors(
        {"__all__": "Email o contraseña incorrectos"}
    )

    assert page("{{ form_error(form) }}", refused).count("Email o contraseña incorrectos") == 1
    assert "alert" not in page("{{ form_error(form) }}", FormResult())
    assert "alert" not in page("{{ form_error(form) }}")
    assert "Hola" in page('{{ form_error({"__all__": "Hola"}) }}')  # the old dict form


# --- The pages keep what was typed --------


def test_a_rejected_login_shows_the_address_again_and_never_the_password(
    client: TestClient,
) -> None:
    response = client.post(
        "/login", data={"email": "ana@example.com", "password": "una-clave-mala"}
    )

    assert response.status_code == 400
    assert 'value="ana@example.com"' in response.text
    assert "una-clave-mala" not in response.text


def test_a_rejected_registration_keeps_the_name_and_the_address(client: TestClient) -> None:
    response = client.post(
        "/register", data={"email": "no-es-un-email", "full_name": "Ana", "password": "x"}
    )

    assert response.status_code == 400
    assert 'value="Ana"' in response.text and 'value="no-es-un-email"' in response.text


def test_a_rejected_note_keeps_title_and_body_in_a_textarea(logged_in_client: TestClient) -> None:
    response = logged_in_client.post("/notes", data={"title": "", "body": "Lo que escribí\ny más"})

    assert response.status_code == 400
    assert "<textarea" in response.text and "Lo que escribí" in response.text


# --- Flash messages --------


def test_a_flash_is_signed_and_forgeries_stale_or_foreign_values_are_ignored() -> None:
    settings = get_settings()
    value = sign_flash({"category": "success", "title": "Hecho"}, settings)

    assert unsign_flash(value, settings) == {"category": "success", "title": "Hecho"}
    assert unsign_flash(value[:-2] + "xx", settings) is None
    assert unsign_flash("no-es-nada", settings) is None
    other = settings.model_copy(
        update={"secret_key": "otra-clave-distinta-de-treinta-y-dos-caracteres"}
    )
    assert unsign_flash(value, other) is None


def test_a_session_cookie_cannot_be_replayed_as_a_flash() -> None:
    from app.security import sign_session_token

    assert unsign_flash(sign_session_token("un-token", get_settings()), get_settings()) is None


def test_creating_a_note_says_so_on_the_next_page_once(logged_in_client: TestClient) -> None:
    created = logged_in_client.post("/notes", data={"title": "Compras", "body": "Leche"})

    assert created.status_code == 303
    assert FLASH_COOKIE_NAME in created.cookies

    first = logged_in_client.get("/notes")
    assert "Nota guardada" in first.text and 'data-category="success"' in first.text
    assert 'role="status"' in first.text
    # The page deleted it: nothing is left to show a second time.
    assert FLASH_COOKIE_NAME not in logged_in_client.cookies or not logged_in_client.cookies.get(
        FLASH_COOKIE_NAME
    )
    assert "Nota guardada" not in logged_in_client.get("/notes").text


def test_a_flash_is_not_eaten_by_an_htmx_fragment(logged_in_client: TestClient) -> None:
    logged_in_client.post("/notes", data={"title": "Compras", "body": "Leche"})

    fragment = logged_in_client.get("/demo/ping", headers={"HX-Request": "true"})
    page = logged_in_client.get("/notes")

    assert "Nota guardada" not in fragment.text and FLASH_COOKIE_NAME not in fragment.headers.get(
        "set-cookie", ""
    )
    assert "Nota guardada" in page.text


def test_a_forged_flash_cookie_shows_nothing_and_is_cleared(client: TestClient) -> None:
    client.cookies.set(FLASH_COOKIE_NAME, "forjada")

    page = client.get("/")

    assert 'class="toast ' not in page.text
    assert FLASH_COOKIE_NAME in page.headers["set-cookie"]


def test_the_text_of_a_flash_is_escaped(db_session, mailbox) -> None:  # type: ignore[no-untyped-def]
    app = create_app(enforce_csrf=False)
    override_dependencies(app, db_session, mailbox)

    @app.get("/avisa")
    def avisa(request: Request) -> Response:
        return flash(
            RedirectResponse("/", status_code=303), get_settings(), HOSTILE, description=HOSTILE
        )

    @app.get("/vista")
    def vista(request: Request) -> Response:
        return render(request, "pages/404.html")

    with TestClient(app, follow_redirects=False) as probe:
        probe.get("/avisa")
        html = probe.get("/vista").text

    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;" in html


def test_deleting_a_note_over_htmx_removes_it_and_says_so(
    logged_in_client: TestClient,
    db_session,
    user,  # type: ignore[no-untyped-def]
) -> None:
    note = NoteRepository(db_session).create(user_id=user.id, title="Temporal", body="x")
    db_session.flush()

    response = logged_in_client.delete(f"/notes/{note.id}", headers={"HX-Request": "true"})

    assert response.status_code == 200 and "HX-Reswap" not in response.headers
    assert 'data-category="success"' in response.text and "Nota eliminada" in response.text
