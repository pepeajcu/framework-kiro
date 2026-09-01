"""Smoke tests: the skeleton is standing.

These are deliberately about the framework's own guarantees rather than any
business feature. Keep them: they are what catches a broken base template or a
missing asset before it reaches a page anyone cares about.
"""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_health_reports_ok(client: TestClient) -> None:
    """The liveness probe answers — this is what the container healthcheck hits."""
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_home_renders_server_side(client: TestClient) -> None:
    """The home page arrives as complete HTML from the server.

    This is the SEO guarantee in test form: the visible content must be in the
    response body, not injected later by JavaScript.
    """
    response = client.get("/")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "Hola," in response.text
    assert "<h1" in response.text


def test_home_includes_seo_metadata(client: TestClient) -> None:
    """Title, description, canonical and Open Graph tags are present."""
    html = client.get("/").text

    assert "<title>" in html
    assert 'name="description"' in html
    assert 'rel="canonical"' in html
    assert 'property="og:title"' in html


def test_htmx_fragment_is_not_a_full_document(client: TestClient) -> None:
    """HTMX endpoints return fragments, never whole pages.

    Returning a full document here would nest `<html>` inside the live page —
    it renders, so the mistake survives review, and then breaks in subtle ways.
    """
    response = client.get("/demo/ping", headers={"HX-Request": "true"})

    assert response.status_code == 200
    assert "<!doctype html>" not in response.text.lower()
    assert "Respuesta del servidor" in response.text


def test_unknown_url_renders_the_404_page(client: TestClient) -> None:
    """A 404 is a real page with the site's layout, not a plain-text default."""
    response = client.get("/esta-url-no-existe")

    assert response.status_code == 404
    assert "Esta página no existe" in response.text
