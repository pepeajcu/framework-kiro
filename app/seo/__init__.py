"""Sitemap and robots.txt.

    from app.seo.sitemap import SitemapEntry, register_sitemap_provider

    def blog_posts(db: Session) -> Iterable[SitemapEntry]:
        for post in PostRepository(db).list_published():
            yield SitemapEntry(loc=f"/blog/{post.slug}", lastmod=post.updated_at.date())

    register_sitemap_provider(blog_posts)

Kiro ships with no business entities of its own, so `/sitemap.xml` starts with
just the static pages the framework knows about. A generated project adds its
own public pages by registering a provider — see ADR-0012 — instead of the
sitemap route growing a query per model.
"""
