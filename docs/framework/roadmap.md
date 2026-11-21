# Roadmap

**FRAMEWORK-ONLY** — `setup.sh` elimina esta carpeta de los proyectos generados.

## v0.1.0 — Esqueleto  *(publicada — 2026-09-03)*

Lo mínimo para usar Kiro en un proyecto real y validar el flujo con la IA.

- [x] `setup.sh`: preflight, prompts, secretos, tokens, modo no interactivo,
      detección de puertos libres, idempotencia
- [x] Docker Compose con PostgreSQL 18 y healthcheck
- [x] Dockerfile multi-etapa: sin Node, sin privilegios, con healthcheck
- [x] `config.py`, `db.py`, `deps.py`, `exceptions.py`
- [x] `BaseRepository` genérico y tipado
- [x] Alembic con convención de nombres de constraints
- [x] Basecoat + HTMX vendorizados, Tailwind sin Node
- [x] `base.html` con SEO: canonical, Open Graph, páginas 404/500
- [x] `AGENTS.md`, `CLAUDE.md`, `PROJECT.md`
- [x] Skills: `kiro-feature`, `kiro-component`, `kiro-migration`, `kiro-adr`
- [x] Comandos: `/spec-new`, `/spec-design`, `/spec-tasks`, `/spec-build`, `/kiro-check`
- [x] Tests con base aislada y rollback por test
- [x] `make check`: lint + tipos + tests + migraciones
- [x] CI: puerta de calidad + e2e que genera un proyecto y corre su suite
- [x] ADRs 0001–0007
- [x] Prueba real: sesión nueva de IA sobre un proyecto generado, sin contexto
      — de ahí salieron todos los fallos de la sección «Corregido» del CHANGELOG

## v0.2.0 — Auth, correo y seguridad  *(publicada — 2026-09-03)*

- [x] Modelos `User`, `Role`, `Session`, `PasswordResetToken`
      — el de sesión se llama **`UserSession`**: este código está lleno de
      `sqlalchemy.orm.Session` y dos cosas con el mismo nombre en el mismo
      archivo cuestan una tarde ([ADR-0008](../decisions/0008-sesiones-en-base-de-datos.md))
- [x] Registro y login con argon2id
- [x] Sesión por cookie firmada + registro en BD (revocable)
- [x] Recuperación de contraseña con token de un solo uso, hasheado y con caducidad
- [x] `require_role`, seed de admin
- [x] **CSRF** de doble envío, integrado con HTMX vía `hx-headers`
- [x] Rate limiting en login y recuperación
- [x] Headers de seguridad: CSP, HSTS, X-Frame-Options
- [x] `request_id` + logging estructurado, con log de acceso propio
- [x] ADRs 0008–0010
- [x] El e2e corre la suite entera del proyecto generado, no solo lint y tipos
- [x] `EmailSender` como Protocol; adaptadores console, Resend y SMTP
- [x] Plantillas de correo editables

## v0.3.0 — Analítica y SEO  *(publicada — 2026-09-07)*

- [x] GTM condicionado a `GTM_ID`
- [x] GA4 Measurement Protocol server-side
- [x] Meta Conversions API server-side con hashing de PII
- [x] `sitemap.xml` dinámico desde la base de datos + `robots.txt`
- [x] Verificación de Search Console
- [x] Banner de consentimiento con HTMX, sin librerías
- [x] ADRs 0011–0012

## v1.0.0 — Listo para publicar  *(publicada — 2026-09-07)*

- [x] Documentación completa y README en inglés — raíz bilingüe
      (`README.md` en inglés, `README.es.md` en español)
- [x] Proyecto de ejemplo con un CRUD completo — "Notes"
      (`app/routers/notes.py` y sus capas), marcado como removible
- [x] Auditoría de seguridad y `pip-audit` — integrado como `make audit` y
      paso de CI; sin hallazgos
- [x] Decidir el nombre público definitivo (ADR-0006) — se conserva "Kiro"
- [x] Tag y publicación

## v1.2.0 — Motor de diseño  *(publicada — 2026-10-13)*

- [x] `design.toml` y compilador puro (`app/design_engine/`): paleta completa en
      OKLCH con contraste AA resuelto, fuentes locales, tema, cabecera, motion
- [x] Layouts `app`/`landing`, cuatro arquetipos de cabecera, `nav_auth` aparte
- [x] `make font`, `make design build|watch|init|set`, `make design-check`
- [x] Motion declarativo por niveles (propio, Motion One, GSAP) con descarga
      verificada por SHA-256
- [x] `/_design` y los comandos `/kiro-design-review` y `/kiro-redesign`
- [x] Once estilos, catálogos de arquetipos y parejas tipográficas
- [x] ADRs 0014–0015
- [x] Tag y publicación

## v1.3.0 — Cimientos, diseño multifuente y kit iOS  *(implementada, sin publicar)*

Plan completo en [`docs/optimizacion/plan-v2.md`](../optimizacion/plan-v2.md).

- [x] **Fase 1 — Cimientos:** `make check` = CI, `make archcheck` (K1-K8, J1-J5),
      contrato de errores y avisos de HTMX, escapado de `.jinja`, cabeceras en el 500
      ([ADR-0016](../decisions/0016-make-check-es-ci-y-reglas-comprobadas.md),
      [ADR-0017](../decisions/0017-errores-y-avisos-de-htmx.md))
- [x] **Fase 2 — Constitución de diseño y tubería única** (`DesignBrief` → `propose` →
      `design-apply`, reglas `P1`-`P10`, `[rules] allow`, preset `estandar-shadcn`;
      [ADR-0018](../decisions/0018-constitucion-de-diseno-y-tuberia-unica.md))
- [x] **Fase 3 — uupm integrado y juez determinista** (asesor vendorizado, `make design-advise`,
      bloque `kiro:a11y`, `tests/test_ux_floor.py`; [ADR-0019](../decisions/0019-uupm-vendorizado-con-solapamiento.md))
- [x] **Fase 4 — Kit iOS completo y `surface = "auto"`** (preset `ios`, kit compilado,
      `components/ios.html.jinja`, cabecera `ios-bar`, fuente del sistema;
      [ADR-0020](../decisions/0020-kit-ios-superficie-auto-y-fuente-del-sistema.md))
- [x] **Fase 5 — Entradas externas** (`/kiro-style`, `make design-reference`, lector de DESIGN.md
      de Refero/skillui/Stitch, captura de webs, envoltorio de skillui;
      [ADR-0021](../decisions/0021-referencias-externas-un-lector-y-candados.md))
- [x] **Fase 6 — Avisos tras redirección y formularios con memoria** (`validate_form`, cookie
      flash firmada, macros `textarea`/`select`/`checkbox`;
      [ADR-0022](../decisions/0022-formularios-con-memoria-y-avisos-tras-redireccion.md))
- [x] **Fase 7 — Densidad compilada y estados** (`[structure] density`, bloque `kiro:rhythm`,
      `components/states.html.jinja`; [ADR-0023](../decisions/0023-densidad-compilada-y-estados.md))

## Fuera de alcance por ahora

- **Ecommerce y pagos** — entra como flag opcional cuando haya un proyecto real
  que lo pida.
- **Multi-tenancy** — añadirlo mal contamina todos los modelos.
