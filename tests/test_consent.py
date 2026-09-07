"""Tests for the cookie-consent banner."""

from __future__ import annotations

from app.services.consent import CONSENT_COOKIE


def test_banner_shows_when_no_decision_has_been_made(client):
    response = client.get("/")

    assert b"data-cookie-banner" in response.content


def test_banner_is_hidden_once_a_decision_is_recorded(client):
    client.cookies.set(CONSENT_COOKIE, "accepted")

    response = client.get("/")

    assert b"data-cookie-banner" not in response.content


def test_accepting_sets_the_cookie(client):
    response = client.post("/consent", data={"decision": "accepted"})

    assert response.status_code == 200
    assert response.content == b""
    assert client.cookies.get(CONSENT_COOKIE) == "accepted"


def test_rejecting_sets_the_cookie_too(client):
    """Rejecting is also a decision — the banner must not show again."""
    client.post("/consent", data={"decision": "rejected"})

    assert client.cookies.get(CONSENT_COOKIE) == "rejected"

    home = client.get("/")
    assert b"data-cookie-banner" not in home.content
