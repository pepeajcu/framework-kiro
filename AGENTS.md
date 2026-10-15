# AGENTS.md — __KIRO_PROJECT_NAME__

Instructions for AI agents working in this repository. Claude Code, OpenCode,
Codex and Cursor all read this file (Claude Code via `CLAUDE.md`, which imports it).

**Read `PROJECT.md` before writing any code.** It holds the business domain:
entities, rules, decisions already made. This file tells you *how* to build;
`PROJECT.md` tells you *what*.

**Read `DESIGN.md` before writing any template.** It holds the brand: style, the
three design dials, the visual signature, the archetypes, the logo. Load the
`kiro-design` skill with it. `design.toml` is its machine half (colours, fonts,
theme, header, motion level): `make design build` compiles it. Without them
every Kiro project looks the same.

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
make check      # lint + types + css + design contract + archcheck + tests + migration drift
make archcheck  # the hard rules below, checked by machine (K1-K8, J1-J5)
make test       # tests only
make revision m="add providers table"   # generate a migration from the models
make migrate    # apply migrations
make css        # rebuild Tailwind after editing templates
make logo src=./logo.svg                  # set the brand logo (path or URL)
make brand-colors primary="#0F766E"       # brand colour (+ neutral=, surface=, secondary=, radius=)
make font name="Fraunces" weights="400,600" role=display   # a local font from Fontsource
make design-init preset=brutalista        # start the whole identity from a style
make design build                         # compile design.toml: CSS, fonts, motion (idempotent)
make design-check                         # does design.toml match what the project ships?
make design-advise q="landing de un spa"   # ask the uupm advisor for a design system and propose it
make design-ux q="form errors" domain=ux   # a uupm guideline, as text (domains: ux chart landing style color typography product)
make design-reference url=https://...      # take a reference's visual language (also md=, skillui=, skillui_dir=)
make design-propose from=brief.json       # turn a design brief into a proposal (.design/proposals/)
make design-apply proposal=<name>         # apply it: design.toml + DESIGN.md + build + check
```

The identity commands all rewrite `design.toml` and rebuild; `/_design` (dev
only) shows the result. See `.claude/skills/kiro-design/SKILL.md`.

Always run `make check` before reporting work as done. It is what CI runs
(CI adds `pip-audit` and the Docker build).

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
| `app/templates/` | Jinja2. `layouts/` page shells, `pages/` full pages, `partials/` HTMX fragments |
| `app/design_engine/` | Compiles `design.toml` into CSS, fonts and motion scripts. Pure and tested |
| `app/emails/` | Transactional email: one adapter per provider, plus rendering |
| `app/security.py` | argon2 hashing, opaque tokens, session cookie flags |
| `app/middleware/` | request id, security headers, CSRF cookie |
| `app/hypermedia.py` | What an HTMX call gets back: error toasts, `toast_response`, `error_response` |

**Reads may skip the service; writes may not.** A page that only lists or shows
rows can call a repository from its router. Anything that creates, changes or
deletes goes through a service, even a one-line one: that is where the next rule
will land (K4).

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
10. **Every page handler declares `user`** — `OptionalUser` on public pages,
    `CurrentUser` on private ones. That dependency is what resolves the session
    cookie; without it the header renders as if nobody were logged in. A POST
    that re-renders its form with a 400 is a page handler too.

### Checked by machine

`make archcheck` (part of `make check`) fails with the file, the line, what to do
instead and the rule it breaks. It is stdlib only (`scripts/archcheck.py`).

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

A genuine exception is allowed, with a reason, and it is listed in every run.
Without the reason after the dash it does not count:

```python
# kiro: allow K6 — awaits the payment provider (next commit)
@router.post("/webhook")
```

```jinja
{# kiro: allow J5 — the widget has no self-hosted build #}
```

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

## Authentication

Sessions are rows in `user_sessions`; the cookie carries a signed, opaque token
and the table stores only its SHA-256. That is what makes a session revocable —
a password change closes every one of them, which a self-contained token cannot
do. Do not replace it with a JWT.

```python
from typing import Annotated
from fastapi import Depends
from app.deps import CurrentUser, OptionalUser, require_role
from app.models.user import User

AdminUser = Annotated[User, Depends(require_role("admin"))]


@router.get("/")  # public — but the header knows who you are
def home(request: Request, user: OptionalUser) -> HTMLResponse: ...


@router.get("/panel")  # anonymous → 303 to /login?next=…
def panel(request: Request, user: CurrentUser) -> HTMLResponse: ...


@router.get("/admin")  # logged in without the role → 403 page
def admin(request: Request, user: AdminUser) -> HTMLResponse: ...
```

Rules that are not obvious from the code:

- **Never hash a password or mint a token by hand.** `app/security.py` owns
  argon2id and the token helpers. One module means one place to audit.
- **Never query `users` outside `UserRepository`.** It normalises the address;
  skip it once and `Ana@x.com` becomes a second account nobody can log into.
- **Never reveal whether an address has an account.** A wrong password, an
  unknown address and a disabled account all produce the same message, and
  `/forgot-password` renders the same page either way. This is a requirement,
  not a nicety: the alternative is a form that enumerates your users.
- **A form POST answers 303 on success** (post/redirect/get) and re-renders the
  form with a 400 on failure. Never 200 on a rejected form. `validate_form(Model, ...)`
  (`app/schemas`) returns the model or a `FormResult` with what was typed and the
  errors (never passwords); the form macros read it (`form=form`). `flash(response,
  settings, "...")` (`app/hypermedia.py`) makes the next page show a one-time toast.
- **Changing a password revokes every session and every pending reset link.**
  `AuthService.set_password` already does it; do not bypass it.

## Forms and CSRF

**Every form that POSTs needs one line**, or the request comes back 403:

```jinja
<form method="post" action="/providers/new">
  {% include "components/csrf_field.html" %}
  ...
</form>
```

An `include`, not a macro: Jinja macros do not see the template context unless
imported `with context`, and forgetting that renders an empty token and fails at
submit time with a 403 that explains nothing.

**HTMX needs nothing.** `base.html` puts the token on the body via `hx-headers`,
so every `hx-post` on the page already carries it.

Validation is a global dependency in `app/main.py`, so a new route is protected
by existing. Do not add per-route CSRF checks, and do not read the form inside a
middleware — that consumes the request body and the handler receives nothing.

## Hardening you get for free

Set up once in `create_app`; you do not call any of it, but know it is there:

- **Security headers** on every response, the 500 page included
  (`app/middleware/security_headers.py`).
  The CSP lives in a dict you can edit. It carries `'unsafe-inline'` in
  `script-src` because Basecoat's dialog, command and toast macros ship inline
  `onclick` handlers — see ADR-0010 before "fixing" that.
- **A request id** on every request, echoed in `X-Request-ID`, attached to every
  log line, and printed on the 500 page. Log with `extra={...}` and the fields
  travel into the JSON.
- **Rate limiting** on login and password reset, counted in PostgreSQL per IP
  *and* per account. To limit something else, use `RateLimiter` from
  `app/services/rate_limit.py`; do not count in a module-level dict, which
  resets on deploy and counts separately in each worker.

## Transactional email

Never instantiate a provider by hand and never read `EMAIL_PROVIDER` outside
`app/config.py`. Inject the sender and render a template:

```python
from app.deps import Emailer
from app.emails import render_email


def send_reset_link(emailer: Emailer, address: str, url: str) -> None:
    emailer.send(render_email("password_reset", to=address, reset_url=url, expires_in_minutes=30))
```

Each email is **two files** in `app/templates/emails/`: `<name>.html`, which
must declare `{% block subject %}`, and `<name>.txt`. The plain-text one is not
optional — a message without it looks empty in clients that block HTML. The
subject lives in the template so that rewriting a message never means editing a
service.

`EMAIL_PROVIDER=console` (the default) prints emails to stdout instead of
sending them. Nothing leaves a developer machine.

**The HTTP library is `httpx2`, not `httpx`.** `import httpx` raises
`ModuleNotFoundError`: the installed package is httpx2, the successor, and it
exposes that module name. It covers both outgoing calls and Starlette's
`TestClient`.

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
extends a layout. See `app/routers/pages.py:demo_ping` for a working example.

**Errors answer an HTMX call with a toast, not a page.** A network failure, a timeout or a
proxy's 502 never reach the app, so `app/static/js/kiro-htmx.js` (loaded by `base.html`) shows
the same kind of toast for those. Raise the domain
exceptions as usual; `app/main.py` answers a navigation with the error page and an
HTMX call with a toast (`HX-Reswap: none` plus an out-of-band swap into
`#toaster`), same status code. For your own message:

```python
from app.hypermedia import toast_response

return toast_response(request, title="Nota archivada", category="success")
```

The toast is rendered by Jinja, which escapes the text. **Never** call
`toaster.toast({...})` from JavaScript with text a visitor can influence:
Basecoat's JS builds it as raw HTML. `base.html` tells HTMX which 4xx/5xx codes
to swap (400, 403, 404, 405, 409, 422, 429, 500); if you start emitting another, add it
to the `htmx-config` tag there, or the response is silently dropped.

Jinja escapes `.html`, `.htm`, `.xml` **and `.jinja`** files (`app/templating.py`);
a new template extension is a decision, not a default.

**Pages extend a layout, not `base.html`.** `layouts/app.html` (centred
container: private screens, lists, forms) or `layouts/landing.html` (full-bleed
sections, loads motion). The header is an archetype chosen in `design.toml`
(`partials/headers/`); the session logic (user, logout, login) lives in
`partials/nav_auth.html` and must not be rewritten when restyling.

**Identity lives in tokens, not in templates.** Colour, greys, surface, radius,
fonts, Basecoat theme, header and motion level are set in `design.toml`
(`make brand-colors`, `make font`, `make design-set`, `make design build`), the
logo with `make logo src=<path|url>` (SVG, or PNG 1:1, in `app/static/brand/`).
Templates use `bg-primary`, `text-muted-foreground`… and `brand_logo()`; never a
hard-coded hex or a logo file name. Never edit inside the `kiro:*` blocks of
`input.css`: they are regenerated on every build.

**Rhythm is a utility, not a number you pick per page:** `section-y`, `gap-rhythm` and
`min-h-row` follow `[structure] density` in `design.toml`. The three states every list and
form needs (loading, empty, error) are `components/states.html.jinja`.

**Motion is attributes, never page JavaScript:** `data-motion="reveal"`,
`"stagger"`, `"split-reveal"`, `"count"`… The level in `design.toml` decides what
runs; content is always visible without JS and under reduced motion.

Design rules (anti-slop, dials, signature, archetypes, fonts without CDN) are in
`.claude/skills/kiro-design/SKILL.md`. When two design sources disagree (taste,
uupm, a preset, a reference) the table in
`.claude/skills/kiro-design/references/constitution.md` says who wins: accessibility,
touch and performance never give way; the generic-pattern rules (`P1`-`P10`) can be
allowed on purpose in `[rules] allow`. `home.html` is scaffolding, not a model
to imitate: build real pages from `DESIGN.md`.

After editing any template, run `make css`: Tailwind scans templates for class
names and drops anything it does not find.

## What NOT to do

- Do not add Django, Flask, SQLModel, or another ORM.
- Do not add React, Vue, Alpine, or a build step for JavaScript.
- Do not add `package.json` or npm. There is no Node.js in this project (ADR-0005).
- Do not load libraries from a CDN. Vendor them into `app/static/` (ADR-0005).
  The motion libraries (Motion, GSAP) are the one managed exception: `make design
  build` downloads them pinned and verified, per project (ADR-0015).
- Do not write animation scripts in a page, or hide content yourself waiting for
  JS. Use `data-motion`.
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
2. `DESIGN.md` and `design.toml` — the brand. If `DESIGN.md` still has TODOs, or
   `make design-check` reports the defaults, ask the user to run `/kiro-init`
   rather than inventing a visual identity.
3. `docs/decisions/` — why the stack is what it is (ADR-0014 and 0015 for the
   design engine and motion).
4. `app/routers/pages.py` and `app/templates/pages/home.html` — a working
   end-to-end example of the plumbing (not of how a page should look).
