---
name: kiro-feature
description: The golden path for adding a feature to a Kiro project — model, migration, repository, schema, service, router, template, test, in that order with working code. Use whenever adding or extending a feature that touches the database or adds a page.
---

# Adding a feature to a Kiro project

Follow these steps in order. Skipping the order causes rework: the migration
depends on the model, the repository on the migration, the template on the router.

Before starting, read `PROJECT.md`. If the entity you are about to create is not
described there, ask the user instead of inventing its fields.

## 1. Model

`app/models/provider.py`:

```python
"""Provider model."""

from __future__ import annotations

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Provider(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A vendor listed in the directory."""

    __tablename__ = "providers"

    name: Mapped[str] = mapped_column(String(120), index=True)
    slug: Mapped[str] = mapped_column(String(140), unique=True)
    description: Mapped[str | None] = mapped_column(Text, default=None)
    is_active: Mapped[bool] = mapped_column(default=True)
```

Notes that matter:
- `Mapped[str]` is NOT NULL; `Mapped[str | None]` is nullable. The annotation is
  the source of truth — there is no separate `nullable=` to keep in sync.
- Always give `String` a length. `Text` for unbounded content.
- Mixin order: `UUIDPrimaryKeyMixin, TimestampMixin, Base`.

**Then register it** in `app/models/__init__.py`:

```python
from app.models.base import Base
from app.models.provider import Provider

__all__ = ["Base", "Provider"]
```

Forgetting this makes Alembic generate a migration that drops the table.

## 2. Migration

```bash
make revision m="add providers table"
```

**Read the generated file before committing it.** Autogenerate misses things
routinely: it does not detect renames (it emits drop + create, losing data), and
it cannot infer data backfills. Check that `downgrade()` actually reverses
`upgrade()`.

```bash
make migrate          # apply
make migrations-check # confirm models and migrations agree
```

## 3. Repository

`app/repositories/provider.py`:

```python
"""Provider data access."""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import select

from app.models.provider import Provider
from app.repositories.base import BaseRepository


class ProviderRepository(BaseRepository[Provider]):
    """Queries over providers."""

    model = Provider

    def get_by_slug(self, slug: str) -> Provider | None:
        """Look a provider up by its URL slug."""
        stmt = select(Provider).where(Provider.slug == slug)
        return self.session.scalars(stmt).one_or_none()

    def list_active(self, *, limit: int = 50) -> Sequence[Provider]:
        """Active providers, newest first."""
        stmt = (
            select(Provider)
            .where(Provider.is_active.is_(True))
            .order_by(Provider.created_at.desc())
            .limit(limit)
        )
        return self.session.scalars(stmt).all()
```

`BaseRepository` already gives you `get`, `get_or_raise`, `list`, `count`,
`exists`, `create`, `update`, `delete`. Only add methods for queries it lacks.

**This is the only file allowed to build SQLAlchemy statements for providers.**

## 4. Schemas — only if there is form input

`app/schemas/provider.py`:

```python
"""Provider input/output schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ProviderCreate(BaseModel):
    """Payload accepted by the provider creation form."""

    name: str = Field(min_length=2, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
```

## 5. Service — only if there is logic beyond CRUD

Put it in `app/services/provider.py` when there are rules to enforce (uniqueness,
state transitions, side effects). Services receive a `Session`, build the
repositories they need, and raise domain exceptions from `app/exceptions.py`.
Skip this layer for plain CRUD — an empty pass-through service is noise.

## 6. Router

`app/routers/providers.py`:

```python
"""Provider pages."""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from app.deps import DbSession, OptionalUser
from app.repositories.provider import ProviderRepository
from app.templating import render

router = APIRouter(prefix="/providers", tags=["providers"], include_in_schema=False)


@router.get("/", response_class=HTMLResponse)
def list_providers(request: Request, db: DbSession, user: OptionalUser) -> HTMLResponse:
    """Directory of active providers."""
    providers = ProviderRepository(db).list_active()
    return render(request, "pages/providers/list.html", {"providers": providers})


@router.get("/{slug}", response_class=HTMLResponse)
def provider_detail(request: Request, db: DbSession, user: OptionalUser, slug: str) -> HTMLResponse:
    """A single provider's page."""
    provider = ProviderRepository(db).get_by_slug(slug)
    if provider is None:
        raise NotFoundError("Provider", slug)  # renders the 404 page
    return render(request, "pages/providers/detail.html", {"provider": provider})
```

`user: OptionalUser` on every page handler, even public ones — it is what
resolves the session cookie and therefore what makes the header show who is
logged in. Use `CurrentUser` where the page requires an account, and
`Annotated[User, Depends(require_role("admin"))]` where it requires a role.

Register it in `app/main.py`:

```python
from app.routers import health, pages, providers

...
app.include_router(providers.router)
```

## 7. Templates

Full page in `app/templates/pages/providers/list.html`:

```jinja
{% extends "base.html" %}

{% block title %}Providers — {{ settings.app_name }}{% endblock %}
{% block description %}Directory of active providers.{% endblock %}

{% block content %}
<h1 class="text-3xl font-semibold tracking-tight">Providers</h1>

<div class="mt-6 grid gap-4 sm:grid-cols-2">
  {% for provider in providers %}
    <article class="card">
      <header>
        <h2><a href="/providers/{{ provider.slug }}">{{ provider.name }}</a></h2>
      </header>
      <section>
        <p class="text-muted-foreground text-sm">{{ provider.description or "" }}</p>
      </section>
    </article>
  {% else %}
    <p class="text-muted-foreground">No providers yet.</p>
  {% endfor %}
</div>
{% endblock %}
```

A form page needs the CSRF token, or the POST comes back 403:

```jinja
<form method="post" action="/providers/new" class="space-y-4">
  {% include "components/csrf_field.html" %}
  {{ field("name", "Nombre", value=name, errors=errors) }}
  <button class="btn" data-variant="primary" type="submit">Guardar</button>
</form>
```

An `include`, not a macro: Jinja macros do not see the template context unless
imported `with context`, and forgetting that renders an empty token and fails at
submit time. HTMX requests need nothing — `base.html` sends the token in a
header for all of them.

Answer a successful POST with a 303 redirect (post/redirect/get) and a failed
one by re-rendering the form with a 400. `app/routers/auth.py` is the worked
example.

For an HTMX interaction, the fragment goes in `partials/` and does **not**
extend `base.html`:

```jinja
{# app/templates/partials/provider_results.html #}
{% for provider in providers %}
  <article class="card">...</article>
{% endfor %}
```

Run `make css` after adding templates, or new Tailwind classes will be missing.

## 8. Tests

```python
def test_provider_list_renders(client, db_session):
    ProviderRepository(db_session).create(name="Flores GT", slug="flores-gt")
    db_session.flush()

    response = client.get("/providers/")

    assert response.status_code == 200
    assert "Flores GT" in response.text
```

## 9. Finish

```bash
make check
```

Do not report the feature as done until this passes.
