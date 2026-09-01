# Changelog

Todas las versiones notables de Kiro se documentan aquí.
Formato basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/);
versionado según [SemVer](https://semver.org/lang/es/).

> **Cómo leer este changelog si vas a actualizar un proyecto existente**
> (ver [`docs/upgrading.md`](docs/upgrading.md)). Cada entrada lleva una etiqueta:
>
> - `[SEGURO]` — se puede traer con `git checkout upstream/main -- <ruta>` sin más.
> - `[MIGRACIÓN]` — requiere pasos manuales; los pasos están descritos en la entrada.
> - `[RUPTURA]` — cambia contratos existentes. Leer antes de traer nada.

## [Unreleased] — v0.1.0 · Esqueleto

Primera versión utilizable. Un proyecto generado arranca, sirve páginas
renderizadas en servidor, habla con PostgreSQL y pasa su propia puerta de calidad.

### Instalador

- `[SEGURO]` `setup.sh` con preflight (docker, python, git, uv), preguntas
  interactivas, generación de secretos con `openssl`, sustitución de tokens,
  limpieza de archivos del framework y arranque de la base de datos.
- `[SEGURO]` Modo `--non-interactive` con una flag por pregunta. Es lo que
  permite que CI lo ejecute y que el instalador no se pudra en silencio.
- `[SEGURO]` **Detección de puertos libres.** Los valores por defecto de
  PostgreSQL y de la app son el primer puerto disponible, no el canónico: una
  máquina con varios proyectos ya tiene el 5432 y el 8000 ocupados.
- `[SEGURO]` Guarda de idempotencia: correr `setup.sh` dos veces aborta sin
  regenerar `.env` ni dejar la base de datos inaccesible.
- `[SEGURO]` Regenera `uv.lock` tras renombrar el proyecto, para que
  `uv sync --frozen` siga funcionando en CI y en el Dockerfile.

### Aplicación

- `[SEGURO]` `app/config.py` — Settings tipado, único punto que lee el entorno.
- `[SEGURO]` `app/db.py` — engine síncrono con `pool_pre_ping`, sesión por
  petición con commit/rollback automático.
- `[SEGURO]` `app/repositories/base.py` — `BaseRepository[ModelT]` genérico y
  tipado, que falla al importar si una subclase olvida declarar `model`.
- `[SEGURO]` `app/models/base.py` — convención de nombres de constraints y
  claves UUIDv7.
- `[SEGURO]` `app/templating.py` — Jinja2 configurado, helper `render()` y
  `asset()` con cache-busting por mtime.
- `[SEGURO]` `app/exceptions.py` — excepciones de dominio sin acoplar a FastAPI.
- `[SEGURO]` Páginas 404 y 500 renderizadas con el layout del sitio.

### Frontend

- `[SEGURO]` Basecoat 1.0.2 y HTMX 2.0.10 vendorizados. Cero Node.js: Tailwind
  v4 se compila con su CLI standalone vía `pytailwindcss`.
- `[SEGURO]` `base.html` con SEO de serie: título, descripción, canonical,
  Open Graph y Twitter Card, todo sobreescribible por bloque.
- `[SEGURO]` Página de inicio de ejemplo con una interacción HTMX real,
  pensada como referencia viva para la IA.

### Capa de IA

- `[SEGURO]` `AGENTS.md` con el stack, las capas, las reglas duras y lo
  prohibido. `CLAUDE.md` lo importa.
- `[SEGURO]` Plantilla `PROJECT.md` para el dominio de negocio.
- `[SEGURO]` Skills `kiro-feature`, `kiro-component`, `kiro-migration`, `kiro-adr`.
- `[SEGURO]` Comandos `/spec-new`, `/spec-design`, `/spec-tasks`, `/spec-build`,
  `/kiro-check`.

### Infraestructura y calidad

- `[SEGURO]` Dockerfile multi-etapa: usuario sin privilegios, healthcheck, y el
  CSS compilado en su propia etapa. Imagen de producción de ~390 MB.
- `[SEGURO]` `compose.yml` con PostgreSQL 18 y puertos configurables.
- `[SEGURO]` `make check` — lint, tipos, tests y detección de migraciones
  pendientes.
- `[SEGURO]` Tests con base de datos aislada (`<db>_test`) y rollback por test.
  El esquema se construye con las migraciones reales, no con `create_all()`.
- `[SEGURO]` CI: puerta de calidad + workflow e2e que genera un proyecto desde
  cero con tres combinaciones de opciones y corre su suite.
- `[SEGURO]` Pre-commit con ruff, mypy `--strict` y shellcheck.

### Corregido

Los cuatro salieron de construir un catálogo real sobre el framework, no de
revisar el código: ninguno se detecta sin un proyecto de verdad encima.

- `[SEGURO]` **`make seed` estaba roto.** El Makefile invocaba `scripts.seed`,
  pero ni `scripts/seed.py` ni `scripts/__init__.py` existían — y `setup.sh`
  borra `scripts/lib/`, así que en un proyecto generado la carpeta quedaba
  vacía. Añadido un `seed.py` funcional y documentado, con el patrón idempotente
  (buscar por clave natural y actualizar) explicado en su docstring.
- `[SEGURO]` **La guía de personalización de `input.css` era incorrecta.** El
  ejemplo sugería sobreescribir `--color-primary` dentro de `@theme`. Basecoat
  mapea `--color-primary: var(--primary)` en su propio `@theme`, y el modo
  oscuro cambia la variable CRUDA: sobreescribir el token rompe esa indirección
  y el color deja de cambiar en modo oscuro. Corregido, separando qué va en
  `:root` (colores, radios) y qué en `@theme` (tipografías).
- `[SEGURO]` **La imagen de producción no incluía `scripts/`**, así que no se
  podía sembrar datos en el servidor. Ahora viaja, y `.dockerignore` excluye
  `scripts/lib/` y los `__pycache__` de cualquier profundidad, que sí se colaban.
- `[RUPTURA]` **El LICENSE del framework viajaba a todos los proyectos**, así
  que el sitio de un cliente nacía con el copyright del autor de Kiro. Ahora
  `setup.sh` instala un LICENSE propio con el autor y el año del proyecto. De
  paso, esto le da uso a `--author`, que hasta ahora se preguntaba y no se
  usaba en ningún sitio.
- `[SEGURO]` Ejemplos de la ayuda y de la documentación neutralizados: llevaban
  un dominio real y nombres de proyectos concretos del autor.
- `[SEGURO]` Aviso en `demo_ping` de que al borrarlo se pierde
  `test_htmx_fragment_is_not_a_full_document`, que vigila un invariante real:
  un endpoint HTMX devuelve un fragmento, nunca un documento completo.

- `[SEGURO]` **`migrations/env.py` pisaba la URL fijada por su llamador.** La
  suite de tests apunta Alembic a la base `<db>_test`, pero `env.py` la
  sobreescribía sin comprobarlo: `alembic upgrade` migraba la base de
  DESARROLLO y dejaba la de test vacía. Los tests seguían pasando —no había
  tablas que consultar todavía— y el fallo solo aparecía con la primera
  migración del proyecto, lejos de su causa. Encontrado al construir el primer
  catálogo real sobre el framework.
  Añadido `tests/test_database_isolation.py` como guarda de regresión.

### Decisiones registradas

ADRs 0001–0007. Tres contradicen el documento de visión original y son las que
más importa conocer:

- [0002](docs/decisions/0002-sqlalchemy-sincrono.md) — SQLAlchemy **síncrono**,
  no async: es donde más alucina la IA en este stack.
- [0005](docs/decisions/0005-sin-nodejs.md) — cero Node.js.
- [0007](docs/decisions/0007-sin-alpinejs.md) — sin Alpine.js; Basecoat ya cubre
  la interactividad con JS vanilla.

### Notas sobre dependencias externas

- **PostgreSQL 18** cambió el punto de montaje del volumen a
  `/var/lib/postgresql`. El idiom antiguo (`/var/lib/postgresql/data`) hace que
  el contenedor arranque en bucle.
- **Basecoat 1.0** sustituyó las clases modificadoras por atributos `data-*`:
  `<button class="btn" data-variant="primary">`, no `btn-primary`. Escribir la
  forma antigua no da error, simplemente renderiza sin estilo.
- **Starlette 1.6** marca `httpx` v1 como obsoleta para su `TestClient`. Kiro usa
  `httpx2`, que sirve además para las llamadas HTTP salientes.

[Unreleased]: https://github.com/pepeajcu/framework-kiro/commits/main
