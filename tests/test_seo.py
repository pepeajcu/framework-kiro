"""Tests for robots.txt and sitemap.xml."""

from __future__ import annotations

from xml.etree import ElementTree

from app.config import get_settings


def test_robots_txt_disallows_the_auth_forms_and_points_at_the_sitemap(client):
    response = client.get("/robots.txt")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    body = response.text
    assert "Disallow: /login" in body
    assert "Disallow: /register" in body
    assert "Disallow: /reset-password" in body
    assert f"Sitemap: {get_settings().base_url}/sitemap.xml" in body


def test_sitemap_is_valid_xml_and_lists_the_home_page(client):
    response = client.get("/sitemap.xml")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/xml")

    # Parsing our own app's output, not attacker-controlled input.
    root = ElementTree.fromstring(response.content)  # noqa: S314
    locs = [el.text for el in root.iter("{http://www.sitemaps.org/schemas/sitemap/0.9}loc")]
    assert f"{get_settings().base_url}/" in locs
