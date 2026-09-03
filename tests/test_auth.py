"""Tests for authentication.

These are the tests that decide whether the framework is safe to build on, so
they check behaviour a reviewer cannot see by reading a template: that a
revoked session stops working, that a reset link dies after one use, that a
wrong password and an unknown address are indistinguishable.
"""

from __future__ import annotations

import datetime as dt
from typing import Annotated

import pytest
from fastapi import Depends, FastAPI
from fastapi.responses import PlainTextResponse
from fastapi.testclient import TestClient

from app.config import get_settings
from app.deps import CurrentUser, require_role
from app.main import create_app
from app.models.user import User
from app.repositories.user_session import UserSessionRepository
from app.security import SESSION_COOKIE_NAME
from tests.conftest import PASSWORD, override_dependencies

AdminUser = Annotated[User, Depends(require_role("admin"))]
"""How a project declares a route that only administrators may open."""


# --- Registration -----------------------------------------------------------


def test_register_creates_an_account_and_logs_in(client, db_session):
    response = client.post(
        "/register",
        data={"email": "Nueva@Example.com", "password": PASSWORD, "full_name": "Nueva"},
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/"
    assert client.cookies.get(SESSION_COOKIE_NAME)

    from app.repositories.user import UserRepository

    created = UserRepository(db_session).get_by_email("nueva@example.com")
    assert created is not None
    # Stored lowercased, so the address cannot be registered twice in two cases.
    assert created.email == "nueva@example.com"
    assert created.has_role("user")
    assert PASSWORD not in created.password_hash


def test_register_rejects_an_address_already_taken_in_another_case(client, user):
    response = client.post(
        "/register",
        data={"email": user.email.upper(), "password": PASSWORD, "full_name": ""},
    )

    assert response.status_code == 400
    assert "Ya existe una cuenta" in response.text


def test_register_rejects_a_short_password(client):
    response = client.post(
        "/register",
        data={"email": "corta@example.com", "password": "corta", "full_name": ""},
    )

    assert response.status_code == 400
    assert "al menos" in response.text
    assert not client.cookies.get(SESSION_COOKIE_NAME)


def test_registration_can_be_switched_off(db_session, mailbox):
    """A project without public sign-up should not have a /register page at all."""
    settings = get_settings().model_copy(update={"allow_registration": False})
    app = create_app()
    override_dependencies(app, db_session, mailbox, settings=settings)

    with TestClient(app) as client:
        assert client.get("/register").status_code == 404
        assert client.post("/register", data={"email": "x@y.test"}).status_code == 404


# --- Login ------------------------------------------------------------------


def test_login_sets_a_signed_httponly_cookie(client, user):
    response = client.post("/login", data={"email": user.email, "password": PASSWORD})

    assert response.status_code == 303
    cookie_header = response.headers["set-cookie"]
    assert "HttpOnly" in cookie_header
    assert "SameSite=lax" in cookie_header
    # The raw token never appears in the cookie: what travels is signed.
    assert client.cookies[SESSION_COOKIE_NAME].count(".") >= 1


@pytest.mark.parametrize(
    ("email", "password"),
    [
        ("ana@example.com", "la contraseña equivocada"),
        ("nadie@example.com", PASSWORD),
    ],
    ids=["wrong password", "unknown address"],
)
def test_login_failures_are_indistinguishable(client, user, email, password):
    """A wrong password and an unknown address must look the same.

    Any difference — wording, status code — turns the login form into a way to
    find out who has an account here.
    """
    response = client.post("/login", data={"email": email, "password": password})

    assert response.status_code == 400
    assert "Email o contraseña incorrectos" in response.text
    assert not client.cookies.get(SESSION_COOKIE_NAME)


def test_a_disabled_account_cannot_log_in(client, user, db_session):
    user.is_active = False
    db_session.flush()

    response = client.post("/login", data={"email": user.email, "password": PASSWORD})

    assert response.status_code == 400
    assert not client.cookies.get(SESSION_COOKIE_NAME)


def test_login_returns_to_the_page_that_asked_for_it(client, user):
    response = client.post(
        "/login",
        data={"email": user.email, "password": PASSWORD, "next": "/panel"},
    )

    assert response.headers["location"] == "/panel"


@pytest.mark.parametrize(
    "hostile",
    ["https://evil.example/phish", "//evil.example/phish"],
)
def test_login_refuses_to_redirect_off_site(client, user, hostile):
    """Open redirect guard: `?next=` may only ever be a path on this site."""
    response = client.post(
        "/login",
        data={"email": user.email, "password": PASSWORD, "next": hostile},
    )

    assert response.headers["location"] == "/"


def test_the_header_shows_who_is_logged_in(logged_in_client, user):
    body = logged_in_client.get("/").text

    assert user.email in body
    assert "Salir" in body


def test_logout_revokes_the_session_server_side(logged_in_client, db_session, user):
    response = logged_in_client.post("/logout")

    assert response.status_code == 303
    sessions = UserSessionRepository(db_session).list_active_for_user(user.id)
    assert sessions == []
    # And the browser is no longer treated as logged in.
    assert "Entrar" in logged_in_client.get("/").text


# --- Session validity -------------------------------------------------------


def test_a_tampered_cookie_is_ignored(client, user):
    client.cookies.set(SESSION_COOKIE_NAME, "no-esto-no-lo-firmamos-nosotros")

    assert "Entrar" in client.get("/").text


def test_a_revoked_session_stops_working_immediately(logged_in_client, db_session, user):
    """The whole reason sessions live in the database instead of in a JWT."""
    assert "Salir" in logged_in_client.get("/").text

    UserSessionRepository(db_session).revoke_all_for_user(user.id)

    assert "Entrar" in logged_in_client.get("/").text


def test_an_expired_session_stops_working(logged_in_client, db_session, user):
    sessions = UserSessionRepository(db_session).list_active_for_user(user.id)
    sessions[0].expires_at = dt.datetime.now(tz=dt.UTC) - dt.timedelta(seconds=1)
    db_session.flush()

    assert "Entrar" in logged_in_client.get("/").text


# --- Guarded pages ----------------------------------------------------------


def guarded_app(db_session, mailbox) -> FastAPI:
    """An app with two protected routes, to exercise the dependencies."""
    app = create_app()
    override_dependencies(app, db_session, mailbox)

    @app.get("/_test/private", response_class=PlainTextResponse)
    def private(user: CurrentUser) -> str:
        return f"privado para {user.email}"

    @app.get("/_test/admin", response_class=PlainTextResponse)
    def admin_only(user: AdminUser) -> str:
        return f"panel de {user.email}"

    return app


def test_a_protected_page_sends_anonymous_visitors_to_the_login_form(db_session, mailbox):
    with TestClient(guarded_app(db_session, mailbox)) as client:
        response = client.get("/_test/private", follow_redirects=False)

    assert response.status_code == 303
    # And it remembers where they were going.
    assert response.headers["location"] == "/login?next=/_test/private"


def test_an_htmx_request_gets_a_redirect_header_not_a_login_page(db_session, mailbox):
    """HTMX would otherwise swap the whole login page into a corner of the page."""
    with TestClient(guarded_app(db_session, mailbox)) as client:
        response = client.get("/_test/private", headers={"HX-Request": "true"})

    assert response.status_code == 204
    assert response.headers["HX-Redirect"] == "/login?next=/_test/private"
    assert response.text == ""


def test_a_missing_role_is_a_403_not_a_login_loop(db_session, mailbox, user):
    """Someone logged in without the role must not be sent back to a login form."""
    with TestClient(guarded_app(db_session, mailbox)) as client:
        client.post("/login", data={"email": user.email, "password": PASSWORD})
        response = client.get("/_test/admin")

    assert response.status_code == 403
    assert "Sin permiso" in response.text


def test_an_admin_gets_through(db_session, mailbox, admin):
    with TestClient(guarded_app(db_session, mailbox)) as client:
        client.post("/login", data={"email": admin.email, "password": PASSWORD})
        response = client.get("/_test/admin")

    assert response.status_code == 200
    assert admin.email in response.text


# --- Password recovery ------------------------------------------------------


def reset_url_from(mailbox) -> str:
    """Pull the reset link out of the email that was just sent."""
    for line in mailbox.last.text.splitlines():
        if "/reset-password/" in line:
            return line.strip()
    raise AssertionError("el correo no traía enlace de recuperación")


def test_forgot_password_emails_a_working_link(client, mailbox, user):
    response = client.post("/forgot-password", data={"email": user.email})

    assert response.status_code == 200
    assert "Revisa tu correo" in response.text
    assert mailbox.last.to == user.email

    assert client.get(reset_url_from(mailbox)).status_code == 200


def test_forgot_password_says_the_same_thing_for_an_unknown_address(client, mailbox):
    """Otherwise the form is a way to enumerate every registered address."""
    known = client.post("/forgot-password", data={"email": "ana@example.com"})
    unknown = client.post("/forgot-password", data={"email": "nadie@example.com"})

    assert known.status_code == unknown.status_code == 200
    assert "Revisa tu correo" in unknown.text
    assert mailbox.outbox == []


def test_a_reset_link_works_once(client, mailbox, user):
    client.post("/forgot-password", data={"email": user.email})
    url = reset_url_from(mailbox)
    new_password = "otra contraseña bien larga"

    first = client.post(url, data={"password": new_password, "password_confirm": new_password})
    assert first.status_code == 303

    second = client.post(url, data={"password": new_password, "password_confirm": new_password})
    assert second.status_code == 400
    assert "ya no vale" in second.text


def test_resetting_a_password_closes_every_other_session(client, mailbox, db_session, user):
    """Recovering an account is worth nothing if the intruder stays logged in."""
    intruder = TestClient(client.app)
    intruder.post("/login", data={"email": user.email, "password": PASSWORD})
    assert "Salir" in intruder.get("/").text

    client.post("/forgot-password", data={"email": user.email})
    new_password = "una contraseña completamente nueva"
    client.post(
        reset_url_from(mailbox),
        data={"password": new_password, "password_confirm": new_password},
    )

    assert "Entrar" in intruder.get("/").text


def test_the_new_password_is_the_one_that_works(client, mailbox, user):
    client.post("/forgot-password", data={"email": user.email})
    new_password = "una contraseña completamente nueva"
    client.post(
        reset_url_from(mailbox),
        data={"password": new_password, "password_confirm": new_password},
    )
    client.post("/logout")

    old = client.post("/login", data={"email": user.email, "password": PASSWORD})
    assert old.status_code == 400

    new = client.post("/login", data={"email": user.email, "password": new_password})
    assert new.status_code == 303


def test_mismatched_passwords_are_rejected(client, mailbox, user):
    client.post("/forgot-password", data={"email": user.email})

    response = client.post(
        reset_url_from(mailbox),
        data={"password": "una contraseña larga", "password_confirm": "otra distinta"},
    )

    assert response.status_code == 400
    assert "no coinciden" in response.text


def test_an_expired_link_says_so(client, mailbox, db_session, user):
    from app.models.password_reset_token import PasswordResetToken

    client.post("/forgot-password", data={"email": user.email})
    url = reset_url_from(mailbox)

    token = db_session.query(PasswordResetToken).one()
    token.expires_at = dt.datetime.now(tz=dt.UTC) - dt.timedelta(seconds=1)
    db_session.flush()

    response = client.get(url)
    assert response.status_code == 400
    assert "ya no vale" in response.text


def test_asking_twice_kills_the_first_link(client, mailbox, user):
    """Only one live link at a time, or every click leaves another key in the inbox."""
    client.post("/forgot-password", data={"email": user.email})
    first_url = reset_url_from(mailbox)

    client.post("/forgot-password", data={"email": user.email})
    second_url = reset_url_from(mailbox)

    assert first_url != second_url
    assert client.get(first_url).status_code == 400
    assert client.get(second_url).status_code == 200


# --- Seeding ----------------------------------------------------------------


def test_seeding_an_admin_twice_changes_nothing(db_session):
    from scripts.seed import seed_admin

    settings = get_settings().model_copy(
        update={"admin_email": "admin@example.com", "admin_password": PASSWORD}
    )

    seed_admin(db_session, settings)
    db_session.flush()
    seed_admin(db_session, settings)
    db_session.flush()

    from app.repositories.user import UserRepository

    admins = [u for u in UserRepository(db_session).list() if u.email == "admin@example.com"]
    assert len(admins) == 1
    assert admins[0].has_role("admin")
