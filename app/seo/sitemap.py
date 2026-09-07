"""The sitemap's provider registry.

`/sitemap.xml` (in `app/routers/seo.py`) does not know about any model — it
just calls every function registered here and concatenates the results. That
is what lets a project add a real content type (blog posts, listings, whatever
`PROJECT.md` describes) without touching the route: register a provider next
to the model instead. See ADR-0012.
"""

from __future__ import annotations

import datetime as dt
from collections.abc import Callable, Iterable
from dataclasses import dataclass

from sqlalchemy.orm import Session

SitemapProvider = Callable[[Session], Iterable["SitemapEntry"]]


@dataclass(frozen=True, slots=True)
class SitemapEntry:
    """One `<url>` entry. Only `loc` is required — the rest are optional per spec."""

    loc: str
    lastmod: dt.date | None = None
    changefreq: str | None = None
    priority: float | None = None


_providers: list[SitemapProvider] = []


def register_sitemap_provider(provider: SitemapProvider) -> SitemapProvider:
    """Add a provider to the sitemap. Usable as a plain call or a decorator.

    Providers run in registration order and their results are concatenated —
    there is no de-duplication, so two providers yielding the same `loc` will
    print it twice.
    """
    _providers.append(provider)
    return provider


def all_entries(db: Session) -> Iterable[SitemapEntry]:
    """Every entry from every registered provider, in registration order."""
    for provider in _providers:
        yield from provider(db)


def _static_pages(db: Session) -> Iterable[SitemapEntry]:
    """The pages the framework itself ships. A generated project adds its own."""
    yield SitemapEntry(loc="/", changefreq="weekly", priority=1.0)


register_sitemap_provider(_static_pages)
