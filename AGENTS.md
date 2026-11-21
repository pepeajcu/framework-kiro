# AGENTS.md — __KIRO_PROJECT_NAME__

Instructions for AI agents working in this repository. Claude Code, OpenCode,
Codex and Cursor all read this file (Claude Code via `CLAUDE.md`, which imports it).

**Read `PROJECT.md` before writing any code.** It holds the business domain:
entities, rules, decisions already made. This file tells you *how* to build;
`PROJECT.md` tells you *what*.

**Read `DESIGN.md` before writing any template.** It holds the brand: style, the
three design dials, the visual signature, the archetypes, the logo. Load the
`kiro-design` skill with it. `design.toml` is its machine half (colours, fonts,
theme, header, motion level): `make design build` compiles it.

The architecture below is already built and working. Do not redesign it, do not
propose alternatives, do not spend tokens re-deriving it. Build features on top.

---

## Stack — fixed, do not change without explicit approval

| Layer | Choice |
|---|---|
| Language | Python 3.12+ (`<3.15`), type hints required (`mypy --strict`) |
| Web | FastAPI (sync handlers, `httpx2` for HTTP calls and `TestClient`) |
| Database | PostgreSQL via SQLAlchemy 2.0 **synchronous** (ADR-0002) |
| Migrations | Alembic |
| Validation | Pydantic v2 |
| Templates | Jinja2, server-rendered (`.html`, `.htm`, `.xml`, `.jinja` autoescaped) |
| Interactivity | HTMX + Basecoat vanilla JS + `kiro-ui.js` (`data-ui-*`). **No Alpine, React or Vue** |
| Components | Basecoat 1.0 (`data-variant`, `data-size`), vendored |
| CSS | Tailwind v4 via standalone CLI. **No Node.js anywhere** (ADR-0005) |
| Tests | pytest against isolated `<db>_test` |

## Commands

```bash
make dev                    # run the app with hot reload
make check                  # lint + types + css + design contract + archcheck + tests + migration drift
make archcheck              # the hard rules below, checked by machine (K1-K8, J1-J5)
make test                   # tests only
make revision m="message"   # generate a migration from the models
make migrate                # apply migrations
make css                    # rebuild Tailwind after editing templates
make strip-example          # remove the worked 'notes' CRUD example in one step
make logo src=./logo.svg    # set the brand logo (path or URL)
make brand-colors primary="#0F766E"       # brand colour (+ neutral=, surface=, secondary=, radius=)
make font name="Fraunces" weights="400,600" role=display
make design-init preset=brutalista        # start the whole identity from a style
make design build                         # compile design.toml: CSS, fonts, motion (idempotent)
make design-check                         # does design.toml match what the project ships?
make design-advise q="landing de un spa"  # ask the uupm advisor for a design system and propose it
make design-ux q="form errors" domain=ux  # a uupm guideline, as text
make design-reference url=https://...     # take a reference's visual language
make design-propose from=brief.json       # turn a design brief into a proposal (.design/proposals/)
make design-apply proposal=<name>         # apply it: design.toml + DESIGN.md + build + check
```

Always run `make check` before reporting work as done.

## Architecture & SDD Workflow

Every request follows the same path:

```
router → service → repository → model → Jinja template → HTML
```

| Directory | Responsibility |
|---|---|
| `app/routers/` | HTTP entry. Parse input, call a service, render a template. Thin. |
| `app/services/` | Business logic. No HTTP objects, no SQL. |
| `app/repositories/` | **The only layer that touches the database.** |
| `app/models/` | SQLAlchemy tables |
| `app/schemas/` | Pydantic input/output validation (`validate_form`) |
| `app/templates/` | Jinja2: `layouts/` page shells, `pages/` full pages, `partials/` HTMX fragments |
| `app/design_engine/` | Compiles `design.toml` into CSS, fonts and motion scripts (ADR-0014, ADR-0015) |
| `app/emails/` | Transactional email (`render_email`, `deliver_email`) |
| `app/security.py` | argon2id hashing, opaque tokens, session & CSRF cookie rotation |
| `app/hypermedia.py` | HTMX error/success toasts (`toast_response`, `error_response`, `flash`) |

**Reads may skip the service; writes may not (K4).**
**Workflow by feature size:**
- **Small feature:** follow `.claude/skills/kiro-feature/SKILL.md` directly (model → migration → repository → schema → service → router → template → test → `make check`).
- **Medium feature:** use `/spec-plan` (`docs/specs/NNN-<slug>/plan.md`, single approval stop) → `/spec-build`.
- **Large / high-uncertainty feature:** `/spec-new` → `/spec-design` → `/spec-tasks` → `/spec-build`.

## Hard rules

1. **Never write SQLAlchemy queries in a router or service (K1).** Add a method to `app/repositories/`.
2. **Never commit or roll back outside `app/db.py:get_db` (K2).** `DbSession` uses `scope="function"`, committing before the HTTP response is sent.
3. **Every page is server-rendered.** Content is always visible without JavaScript.
4. **Every model change needs a migration** (`make revision m="..."`) reviewed before committing.
5. **Every model must be imported in `app/models/__init__.py` (K8).**
6. **Only `app/config.py` reads the environment (K5).** Read `request.app.state.settings` or inject `AppSettings`.
7. **Handlers are `def`, not `async def`, unless awaiting I/O (K6).**
8. **snake_case** for files and functions, **PascalCase** for classes.
9. **Strict typing (`mypy --strict`)** across `app/`.
10. **Every page handler declares `user` (`OptionalUser`, `CurrentUser`, or `require_role`) (K7)** — including POST handlers that re-render a `pages/...` template on 400.

### Checked by machine (`make archcheck`)

| ID | Fails when | Rule |
|---|---|---|
| K1 | a router or service imports a query builder or calls `db.execute/scalars/query` | 1 |
| K2 | `.commit()` / `.rollback()` anywhere but `app/db.py` | 2 |
| K3 | services, repositories, models, schemas, design_engine, emails or analytics import `fastapi`/`starlette` | architecture |
| K4 | a router writes (`create/update/delete`) through a repository | architecture |
| K5 | `os.getenv` / `os.environ` outside `app/config.py` | 6 |
| K6 | an `async def` handler has no `await` | 7 |
| K7 | a handler that renders `pages/...` does not declare `OptionalUser`/`CurrentUser`/a role | 10 |
| K8 | a module in `app/models/` is not imported in `app/models/__init__.py` | 5 |
| J1 | a `partials/` template extends, or a `pages/` one extends `base.html` | frontend |
| J2 | a `<form method="post">` without `components/csrf_field.html` | forms |
| J3 | a hex, `rgb()` or `oklch()` colour written in a template | frontend |
| J4 | a Basecoat 0.x class (`btn-primary`, `btn-sm`, `badge-secondary`...) | frontend |
| J5 | an inline `<script>` or a resource from another domain (ADR-0005, ADR-0010) | frontend |

Reasoned waivers require a dash and explanation: `# kiro: allow K6 — reason` or `{# kiro: allow J5 — reason #}`.

## Security, Auth, Forms & Frontend invariants

Full code examples live in `.claude/skills/kiro-feature/SKILL.md` and `.claude/skills/kiro-component/SKILL.md`.

- **Sessions & CSRF:** Sessions live in `user_sessions` (SHA-256 of opaque token; never JWT). `set_session_cookie` and `clear_session_cookie` in `app/security.py` rotate `csrf_token` automatically. Every `<form method="post">` must include `{% include "components/csrf_field.html" %}` (J2); HTMX gets it from `<body hx-headers>`.
- **Account enumeration & rate limiting:** Login (`InvalidCredentialsError`) and `/forgot-password` (`303` to `/forgot-password/sent`) never reveal whether an email is registered. Public `/register` (when `ALLOW_REGISTRATION=true`) logs the new user straight in and therefore shows a field error on duplicate email as a documented UX trade-off. Login success resets only the `login:email:*` bucket, never `login:ip:*`.
- **Forms & PRG:** Every form POST answers `303` on success and `400` on validation failure using `validate_form(Model, ...)`. Send transactional emails via `BackgroundTasks` + `deliver_email(emailer, message)` so slow providers never block responses or roll back rate-limit hits.
- **Templates, components & motion:** Pages extend `layouts/app.html` or `layouts/landing.html` (never `base.html`, J1). Use Basecoat `data-variant` / `data-size` attributes (never `btn-primary`, J4), design tokens from `design.toml` (never hardcoded colours, J3), `section-y`/`gap-rhythm`/`min-h-row` utilities, `components/states.html.jinja` for loading/empty/error states, `data-ui-*` (`kiro-ui.js`) for local tabs/toggles/drawers, and `data-motion` attributes for motion (ADR-0015). Run `make css` after editing templates.
- **Never edit vendored files** (`app/static/css/vendor/`, `app/templates/basecoat/`, `kiro:*` blocks in `input.css`) or add Node.js/CDN scripts.

## Before you start

1. `PROJECT.md` — if it still has `TODO`, ask the user before inventing domain entities.
2. `DESIGN.md` and `design.toml` — if `DESIGN.md` still has `TODO`, ask the user to run `/kiro-init`.
3. `.claude/skills/` — load `kiro-feature`, `kiro-component`, `kiro-design`, `kiro-migration`, or `kiro-adr` for full patterns and code snippets.
