# 0012 — Sitemap por registro de proveedores, no por consulta a un modelo

**Estado:** Aceptada · 2026-09-07

## Contexto

El roadmap pide `sitemap.xml` "dinámico desde la base de datos". Pero Kiro es
un framework sin entidades de dominio propias — `PROJECT.md` está en TODO
hasta que alguien lo rellena — así que `app/routers/seo.py` no puede tener
una consulta a un modelo de negocio que todavía no existe.

Dos formas de resolverlo:

1. **Dejar el sitemap solo con páginas estáticas** hasta que un proyecto real
   lo extienda a mano, editando el router. Funciona, pero cada proyecto
   generado repite la misma cirugía sobre el mismo archivo.
2. **Un registro de proveedores.** El router no sabe qué modelos existen;
   solo itera una lista de funciones que alguien más registró.

## Decisión

**Opción 2.** `app/seo/sitemap.py` define `SitemapEntry` (`loc`, `lastmod`,
`changefreq`, `priority`) y `register_sitemap_provider(fn)`, donde
`fn(db: Session) -> Iterable[SitemapEntry]`. Arranca con un proveedor de
páginas estáticas ya registrado (`/`). `GET /sitemap.xml` en
`app/routers/seo.py` solo llama a `all_entries(db)` y arma el XML — no conoce
ningún modelo, ni el de hoy ni el que un proyecto añada mañana.

Un proyecto con contenido público real registra su propio proveedor donde
vive el modelo, siguiendo el ejemplo del docstring de `app/seo/__init__.py`,
sin tocar el router ni el registro:

```python
from app.seo.sitemap import SitemapEntry, register_sitemap_provider


def blog_posts(db: Session) -> Iterable[SitemapEntry]:
    for post in PostRepository(db).list_published():
        yield SitemapEntry(loc=f"/blog/{post.slug}", lastmod=post.updated_at.date())


register_sitemap_provider(blog_posts)
```

## Consecuencias

- El sitemap "dinámico desde la base de datos" es real en cuanto un proyecto
  registra su primer proveedor — no hay una segunda pieza de infraestructura
  que construir entonces.
- Sin de-duplicación entre proveedores: dos que produzcan la misma `loc` la
  imprimen dos veces. Aceptable mientras el número de proveedores por
  proyecto sea pequeño; si deja de serlo, se revisa.
- El registro es un `list` a nivel de módulo, poblado por import. Un
  proveedor que viva en un módulo que nadie importa nunca se registra — el
  mismo requisito que `app/models/__init__.py` le impone a los modelos, y por
  el mismo motivo.
- `robots.txt` sigue siendo una lista fija en `app/routers/seo.py`
  (`DISALLOWED_PATHS`): las rutas que hay que ocultar de un buscador son las
  del propio framework (los formularios de auth), no las de un modelo de
  negocio, así que no necesita el mismo mecanismo.
