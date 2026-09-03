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

## v0.3.0 — Analítica y SEO  *(siguiente)*

- [ ] GTM condicionado a `GTM_ID`
- [ ] GA4 Measurement Protocol server-side
- [ ] Meta Conversions API server-side con hashing de PII
- [ ] `sitemap.xml` dinámico desde la base de datos + `robots.txt`
- [ ] Verificación de Search Console
- [ ] Banner de consentimiento con HTMX, sin librerías

## v1.0.0 — Listo para publicar

- [ ] Documentación completa y README en inglés
- [ ] Proyecto de ejemplo con un CRUD completo
- [ ] Auditoría de seguridad y `pip-audit`
- [ ] Decidir el nombre público definitivo (ADR-0006)
- [ ] Tag y publicación

## Fuera de alcance por ahora

- **Ecommerce y pagos** — entra como flag opcional cuando haya un proyecto real
  que lo pida.
- **Multi-tenancy** — añadirlo mal contamina todos los modelos.
