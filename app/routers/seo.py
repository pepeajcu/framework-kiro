"""robots.txt and sitemap.xml.

Neither returns HTML — `PlainTextResponse` and a hand-built XML string — so
neither goes through `app.templating.render()`.
"""

from __future__ import annotations

from xml.sax.saxutils import escape

from fastapi import APIRouter, Response
from fastapi.responses import PlainTextResponse

from app.deps import AppSettings, DbSession
from app.seo.sitemap import SitemapEntry, all_entries

router = APIRouter(tags=["seo"], include_in_schema=False)

# Auth flows are forms, not content: thin, near-duplicate across every visitor,
# and worth nothing indexed. `/reset-password` covers `/reset-password/{token}`
# too — robots.txt matches by prefix, not by exact path.
DISALLOWED_PATHS = ("/login", "/register", "/forgot-password", "/reset-password")


@router.get("/robots.txt", response_class=PlainTextResponse)
def robots_txt(settings: AppSettings) -> str:
    """Allow everything except the auth forms, and point at the sitemap."""
    lines = ["User-agent: *"]
    lines += [f"Disallow: {path}" for path in DISALLOWED_PATHS]
    lines.append(f"Sitemap: {settings.base_url}/sitemap.xml")
    return "\n".join(lines) + "\n"


def _url_entry(base_url: str, entry: SitemapEntry) -> str:
    parts = [f"<loc>{escape(base_url + entry.loc)}</loc>"]
    if entry.lastmod is not None:
        parts.append(f"<lastmod>{entry.lastmod.isoformat()}</lastmod>")
    if entry.changefreq is not None:
        parts.append(f"<changefreq>{escape(entry.changefreq)}</changefreq>")
    if entry.priority is not None:
        parts.append(f"<priority>{entry.priority:.1f}</priority>")
    return "<url>" + "".join(parts) + "</url>"


@router.get("/sitemap.xml")
def sitemap_xml(settings: AppSettings, db: DbSession) -> Response:
    """Static pages plus whatever `register_sitemap_provider` callers added."""
    urls = "".join(_url_entry(settings.base_url, entry) for entry in all_entries(db))
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' + urls + "</urlset>"
    )
    return Response(content=xml, media_type="application/xml")
