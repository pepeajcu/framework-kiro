# AGENTS.md — __KIRO_PROJECT_NAME__

Instructions for AI agents working in this repository. Claude Code, OpenCode,
Codex and Cursor all read this file (Claude Code via `CLAUDE.md`, which imports it).

**Read `PROJECT.md` before writing any code.** It holds the business domain:
entities, rules, decisions already made. This file tells you *how* to build;
`PROJECT.md` tells you *what*.

The architecture below is already built and working. Do not redesign it, do not
propose alternatives, do not spend tokens re-deriving it. Build features on top.

---

## Stack — fixed, do not change without explicit approval

| Layer | Choice |
|---|---|
| Language | Python 3.12+, type hints required |
| Web | FastAPI |
| Database | PostgreSQL via SQLAlchemy 2.0 **synchronous** |
| Migrations | Alembic |
| Validation | Pydantic v2 |
| Templates | Jinja2, server-rendered |
| Interactivity | HTMX + Basecoat's vanilla JS. **No Alpine, no React, no Vue** |
| Components | Basecoat (shadcn/ui in plain HTML+Tailwind), vendored |
| CSS | Tailwind v4 via standalone CLI. **No Node.js anywhere** |
| Tests | pytest |

Rationale for every choice is in `docs/decisions/`. Read the relevant ADR before
arguing with a decision; most obvious alternatives were already evaluated and
rejected for a specific reason.

## Commands

```bash
make dev        # run the app with hot reload
make check      # lint + types + tests + migration drift — run before finishing
make test       # tests only
make revision m="add providers table"   # generate a migration from the models
make migrate    # apply migrations
make css        # rebuild Tailwind after editing templates
```

Always run `make check` before reporting work as done. It is what CI runs.

## Architecture

Every request follows the same path. No exceptions:

```
router → service → repository → model → Jinja template → HTML
```

| Directory | Responsibility |
|---|---|
| `app/routers/` | HTTP entry. Parse input, call a service, render a template. Thin. |
| `app/services/` | Business logic. No HTTP objects, no SQL. |
| `app/repositories/` | **The only layer that touches the database.** |
| `app/models/` | SQLAlchemy tables |
| `app/schemas/` | Pydantic input/output validation |
| `app/templates/` | Jinja2. `pages/` full pages, `partials/` HTMX fragments |

## Hard rules

1. **Never write SQLAlchemy queries in a router or service.** Add a method to
   the relevant repository instead. `BaseRepository` in
   `app/repositories/base.py` already provides get / list / count / create /
   update / delete.
2. **Never commit the session in a router.** `app/db.py:get_db` owns the
   transaction: it commits on success and rolls back on any exception.
3. **Every page is server-rendered.** No client-side rendering, ever. SEO is a
   standing requirement — content must be in the HTML the server sends.
4. **Every new model needs a migration** in the same change:
   `make revision m="..."`, then read the generated file before committing it.
   Autogenerate gets things wrong; it is a draft, not an answer.
5. **Every model must be imported in `app/models/__init__.py`.** Alembic only
   sees imported models — a missing import silently generates a DROP TABLE.
6. **Only `app/config.py` reads the environment.** Never `os.getenv` elsewhere.
7. **Handlers are `def`, not `async def`**, unless the body actually awaits
   network I/O. FastAPI runs sync handlers in a threadpool. See ADR-0002.
8. **snake_case** for files and functions, **PascalCase** for classes.
9. Type everything. `mypy --strict` runs over `app/` and must pass.

## Golden path: adding a feature

The skill `.claude/skills/kiro-feature/SKILL.md` has this with full code
examples. In short, in this order:

1. Model in `app/models/`, then import it in `app/models/__init__.py`
2. `make revision m="..."` and review the generated migration
3. Repository in `app/repositories/`, subclassing `BaseRepository[YourModel]`
4. Pydantic schemas in `app/schemas/` if there is form input
5. Service in `app/services/` if there is logic beyond CRUD
6. Router in `app/routers/`, returning `render(request, "pages/...")`
7. Templates: full page in `pages/`, HTMX fragments in `partials/`
8. Tests in `tests/`
9. `make check`

## Frontend specifics

**Basecoat components use `data-*` attributes for variants, not modifier
classes.** This changed in Basecoat 1.0; older shadcn-style class names do not
exist and will silently render unstyled:

```html
<!-- correct -->
<button class="btn" data-variant="primary" data-size="sm">Save</button>
<span class="badge" data-variant="secondary">New</span>

<!-- WRONG — these classes do not exist -->
<button class="btn-primary btn-sm">Save</button>
<span class="badge-secondary">New</span>
```

Variants: `primary`, `secondary`, `outline`, `ghost`, `link`, `destructive`.
Sizes: `xs`, `sm`, `default`, `lg`, `icon`, `icon-sm`, `icon-lg`, `icon-xs`.

Most components are CSS classes only. Nine complex ones ship Jinja macros in
`app/templates/basecoat/` — import them:

```jinja
{% from "basecoat/select.html.jinja" import select %}
{{ select(name="city", items=[{"value": "mad", "label": "Madrid"}]) }}
```

**HTMX pattern.** The server returns HTML fragments, never JSON:

```html
<button hx-get="/providers/search" hx-target="#results" hx-swap="innerHTML">
```

The handler returns a `partials/` template — a fragment, not a document that
extends `base.html`. See `app/routers/pages.py:demo_ping` for a working example.

After editing any template, run `make css`: Tailwind scans templates for class
names and drops anything it does not find.

## What NOT to do

- Do not add Django, Flask, SQLModel, or another ORM.
- Do not add React, Vue, Alpine, or a build step for JavaScript.
- Do not add `package.json` or npm. There is no Node.js in this project (ADR-0005).
- Do not load libraries from a CDN. Vendor them into `app/static/` (ADR-0005).
- Do not convert the codebase to async SQLAlchemy (ADR-0002).
- Do not edit anything under `app/static/css/vendor/` or
  `app/templates/basecoat/` — those are vendored and get overwritten on update.
  Override in `app/static/css/input.css` or `app/templates/components/`.
- Do not run a mail server. Transactional email goes through the provider
  configured in `app/emails/`.
- Do not commit `.env` or any secret.

## Before you start

1. `PROJECT.md` — the domain. If it is still full of TODOs, ask the user to
   fill it in rather than inventing entities.
2. `docs/decisions/` — why the stack is what it is.
3. `app/routers/pages.py` and `app/templates/pages/home.html` — a working
   end-to-end example of the whole pattern.
