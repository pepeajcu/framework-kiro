"""Tests for the hardening layer: CSRF, headers, request ids and rate limiting.

Every one of these guards something that produces no visible symptom when it
breaks. A missing CSRF check, a header that stopped being sent, a limit that
counts nothing — the site looks exactly the same. These tests are the only
thing that notices.
"""

from __future__ import annotations

import datetime as dt
import json
import logging
import re

import pytest
from fastapi.testclient import TestClient

from app.config import Environment, get_settings
from app.logs import HANDLER_NAME, ConsoleFormatter, JsonFormatter
from app.main import create_app
from app.middleware.csrf import CSRF_COOKIE_NAME, CSRF_HEADER_NAME
from app.middleware.request_id import REQUEST_ID_HEADER, request_id_var
from app.middleware.security_headers import CONTENT_SECURITY_POLICY, build_csp
from app.services.rate_limit import RateLimit, RateLimiter
from tests.conftest import PASSWORD, override_dependencies

TOKEN_IN_FORM = re.compile(r'name="csrf_token"\s+value="([^"]+)"')


@pytest.fixture
def strict_client(db_session, mailbox):
    """A client with CSRF enforcement on, the way production runs."""
    app = create_app()
    override_dependencies(app, db_session, mailbox)
    with TestClient(app, follow_redirects=False) as client:
        yield client


def token_from(client: TestClient, path: str = "/login") -> str:
    """Load a page and read the CSRF token out of its form."""
    match = TOKEN_IN_FORM.search(client.get(path).text)
    assert match is not None, "la página no traía campo csrf_token"
    return match.group(1)


# --- CSRF -------------------------------------------------------------------


def test_a_form_post_without_a_token_is_rejected(strict_client, user):
    response = strict_client.post("/login", data={"email": user.email, "password": PASSWORD})

    assert response.status_code == 403
    # And it explains itself: a stale form is not an accusation.
    assert "caducado" in response.text


def test_the_token_rendered_into_the_form_works(strict_client, user):
    token = token_from(strict_client)

    response = strict_client.post(
        "/login",
        data={"email": user.email, "password": PASSWORD, "csrf_token": token},
    )

    assert response.status_code == 303


def test_htmx_can_send_the_token_in_a_header(strict_client, user):
    """The path `hx-headers` on the body uses for every HTMX request."""
    token = token_from(strict_client)

    response = strict_client.post(
        "/login",
        data={"email": user.email, "password": PASSWORD},
        headers={CSRF_HEADER_NAME: token},
    )

    assert response.status_code == 303


def test_a_token_from_a_different_browser_is_useless(strict_client, db_session, mailbox, user):
    """The heart of double submit: the attacker can send the cookie, not read it.

    A token lifted from another visitor's page does not match the cookie this
    browser carries, which is exactly the situation of a cross-site form.
    """
    other = create_app()
    override_dependencies(other, db_session, mailbox)
    with TestClient(other) as another_browser:
        stolen = token_from(another_browser)

    response = strict_client.post(
        "/login",
        data={"email": user.email, "password": PASSWORD, "csrf_token": stolen},
    )

    assert response.status_code == 403


def test_reading_a_page_needs_no_token(strict_client):
    assert strict_client.get("/").status_code == 200
    assert strict_client.get("/login").status_code == 200


def test_the_cookie_is_not_readable_from_javascript(strict_client):
    """HttpOnly is safe here: the token reaches the page from the server."""
    response = strict_client.get("/login")

    cookie = next(h for h in response.headers.get_list("set-cookie") if CSRF_COOKIE_NAME in h)
    assert "HttpOnly" in cookie
    assert "SameSite=lax" in cookie


def test_htmx_requests_carry_the_token_automatically(client):
    """`hx-headers` on the body, so no hx-post has to remember it."""
    body = client.get("/").text

    assert "hx-headers" in body
    assert "X-CSRF-Token" in body


# --- Security headers -------------------------------------------------------


def test_every_response_carries_the_security_headers(client):
    headers = client.get("/").headers

    assert headers["X-Content-Type-Options"] == "nosniff"
    assert headers["X-Frame-Options"] == "DENY"
    assert headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
    assert "geolocation=()" in headers["Permissions-Policy"]


def test_the_content_security_policy_locks_down_the_dangerous_directives(client):
    policy = client.get("/").headers["Content-Security-Policy"]

    # These are the ones that hold even with 'unsafe-inline' in script-src.
    assert "default-src 'self'" in policy
    assert "frame-ancestors 'none'" in policy
    assert "form-action 'self'" in policy
    assert "base-uri 'self'" in policy
    assert "object-src 'none'" in policy


def test_the_policy_renders_from_the_dict(client):
    assert client.get("/").headers["Content-Security-Policy"] == build_csp(
        CONTENT_SECURITY_POLICY
    )


def test_hsts_is_sent_only_once_deployed(db_session, mailbox):
    """Promising HTTPS-only from a plain-HTTP laptop locks you out of your own site."""
    local = create_app(enforce_csrf=False)
    override_dependencies(local, db_session, mailbox)
    with TestClient(local) as client:
        assert "Strict-Transport-Security" not in client.get("/").headers

    deployed_settings = get_settings().model_copy(
        update={"environment": Environment.PRODUCTION}
    )
    deployed = create_app(deployed_settings, enforce_csrf=False)
    override_dependencies(deployed, db_session, mailbox, settings=deployed_settings)
    with TestClient(deployed) as client:
        header = client.get("/").headers["Strict-Transport-Security"]

    assert "max-age=31536000" in header
    # `preload` is close to irreversible; it must never appear by default.
    assert "preload" not in header


# --- Request id -------------------------------------------------------------


def test_every_response_carries_a_request_id(client):
    first = client.get("/").headers[REQUEST_ID_HEADER]
    second = client.get("/").headers[REQUEST_ID_HEADER]

    assert first and second
    assert first != second


def test_an_id_from_a_proxy_is_kept(client):
    """So a request can be followed across the load balancer and the app."""
    response = client.get("/", headers={REQUEST_ID_HEADER: "edge-7f3a91"})

    assert response.headers[REQUEST_ID_HEADER] == "edge-7f3a91"


@pytest.mark.parametrize(
    "hostile",
    ["fake\ninjected log line", "x" * 200, "id with spaces"],
)
def test_a_hostile_incoming_id_is_replaced(client, hostile):
    """The id lands in the logs, so a caller must not be able to write them."""
    response = client.get("/", headers={REQUEST_ID_HEADER: hostile})

    assert response.headers[REQUEST_ID_HEADER] != hostile
    assert "\n" not in response.headers[REQUEST_ID_HEADER]


def test_the_json_formatter_carries_the_request_id_and_the_extras():
    token = request_id_var.set("abc123")
    record = logging.LogRecord(
        name="app.test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="pedido %s confirmado",
        args=("A-17",),
        exc_info=None,
    )
    record.order_id = "A-17"

    payload = json.loads(JsonFormatter().format(record))
    request_id_var.reset(token)

    assert payload["message"] == "pedido A-17 confirmado"
    assert payload["request_id"] == "abc123"
    assert payload["level"] == "INFO"
    # Whatever was passed as extra= travels with the line.
    assert payload["order_id"] == "A-17"


def test_the_console_formatter_stays_readable():
    record = logging.LogRecord(
        name="app.test",
        level=logging.WARNING,
        pathname=__file__,
        lineno=1,
        msg="algo raro",
        args=(),
        exc_info=None,
    )

    line = ConsoleFormatter().format(record)

    assert line.startswith("WARNING")
    assert "algo raro" in line
    assert "{" not in line


def test_the_access_log_records_the_request_with_its_id(client, caplog):
    """One structured line per request — the thing the request id is for."""
    with caplog.at_level(logging.INFO, logger="app.access"):
        client.get("/login")

    record = next(r for r in caplog.records if r.name == "app.access")
    assert record.path == "/login"
    assert record.status == 200
    assert record.method == "GET"
    assert record.duration_ms >= 0


def test_static_files_do_not_fill_the_log(client, caplog):
    with caplog.at_level(logging.INFO, logger="app.access"):
        client.get("/static/css/app.css")

    assert [r for r in caplog.records if r.name == "app.access"] == []


def test_configuring_logging_twice_does_not_duplicate_lines():
    """Two apps in one test process must not make every line appear twice."""
    from app.logs import configure_logging

    root = logging.getLogger()
    configure_logging(get_settings())
    configure_logging(get_settings())

    ours = [h for h in root.handlers if h.get_name() == HANDLER_NAME]
    assert len(ours) == 1
    # And pytest's own capture handler survived, or caplog would be empty
    # in every project that logs.
    assert len(root.handlers) > 1


# --- Rate limiting ----------------------------------------------------------


def test_the_limiter_counts_each_bucket_on_its_own(db_session):
    limiter = RateLimiter(db_session)
    limit = RateLimit(max_attempts=2, window=dt.timedelta(minutes=5))

    limiter.record(["login:ip:1.1.1.1"])
    limiter.record(["login:ip:1.1.1.1"])

    assert limiter.is_blocked(["login:ip:1.1.1.1"], limit)
    assert not limiter.is_blocked(["login:ip:2.2.2.2"], limit)


def test_hits_outside_the_window_no_longer_count(db_session):
    from app.models.rate_limit import RateLimitHit

    limiter = RateLimiter(db_session)
    limit = RateLimit(max_attempts=1, window=dt.timedelta(minutes=5))
    limiter.record(["login:ip:1.1.1.1"])
    assert limiter.is_blocked(["login:ip:1.1.1.1"], limit)

    hit = db_session.query(RateLimitHit).one()
    hit.created_at = dt.datetime.now(tz=dt.UTC) - dt.timedelta(minutes=10)
    db_session.flush()

    assert not limiter.is_blocked(["login:ip:1.1.1.1"], limit)


def test_login_stops_answering_after_too_many_wrong_passwords(db_session, mailbox, user):
    settings = get_settings().model_copy(update={"login_max_attempts": 3})
    app = create_app(enforce_csrf=False)
    override_dependencies(app, db_session, mailbox, settings=settings)

    with TestClient(app, follow_redirects=False) as client:
        for _ in range(3):
            wrong = client.post("/login", data={"email": user.email, "password": "no es"})
            assert wrong.status_code == 400

        blocked = client.post("/login", data={"email": user.email, "password": "no es"})
        # And the real password does not get through either: that is the point.
        with_real_password = client.post(
            "/login", data={"email": user.email, "password": PASSWORD}
        )

    assert blocked.status_code == 429
    assert "Demasiados intentos" in blocked.text
    assert with_real_password.status_code == 429


def test_getting_it_right_clears_the_counter(db_session, mailbox, user):
    """Somebody mistyping their own password twice must not be locked out."""
    settings = get_settings().model_copy(update={"login_max_attempts": 3})
    app = create_app(enforce_csrf=False)
    override_dependencies(app, db_session, mailbox, settings=settings)

    with TestClient(app, follow_redirects=False) as client:
        client.post("/login", data={"email": user.email, "password": "no es"})
        client.post("/login", data={"email": user.email, "password": "tampoco"})
        assert client.post(
            "/login", data={"email": user.email, "password": PASSWORD}
        ).status_code == 303

        client.post("/logout")
        for _ in range(2):
            again = client.post("/login", data={"email": user.email, "password": "no es"})

    # Two more failures after a success: still under the limit, still answering.
    assert again.status_code == 400


def test_reset_requests_are_limited_so_an_inbox_cannot_be_flooded(db_session, mailbox, user):
    settings = get_settings().model_copy(update={"password_reset_max_requests": 2})
    app = create_app(enforce_csrf=False)
    override_dependencies(app, db_session, mailbox, settings=settings)

    with TestClient(app, follow_redirects=False) as client:
        for _ in range(2):
            assert client.post("/forgot-password", data={"email": user.email}).status_code == 200
        blocked = client.post("/forgot-password", data={"email": user.email})

    assert blocked.status_code == 429
    # Two emails, not three.
    assert len(mailbox.outbox) == 2
