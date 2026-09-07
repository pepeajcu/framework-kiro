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

## [0.2.1] — 2026-09-03 · El instalador en una máquina que no es la tuya

Cuatro fallos que solo aparecen al clonar el repositorio en un equipo recién
formateado, donde `setup.sh` se cerraba —o se colgaba— sin dejar claro por qué.
Todo esto vive en `setup.sh` y `scripts/lib/`, que un proyecto generado ya no
tiene: **no hay nada que traer a un proyecto existente**.

### Corregido

- `[SEGURO]` **El slug se calculaba con `sed y/…/…/`, que cuenta bytes cuando la
  configuración regional no es UTF-8** (instalación mínima, contenedor, WSL sin
  locales generados). Ahí sed abortaba con *"strings for `y' command are
  different lengths"*, el slug salía vacío, y la pregunta se repetía con un
  valor por defecto que nunca pasaba la validación: un bucle infinito. Ahora la
  transliteración la hace `python3`, que ya es un requisito del instalador.
- `[SEGURO]` **`prompt::ask` se colgaba en bucle** cuando el valor por defecto no
  pasaba la validación y no había stdin para corregirlo. Ahora aborta con un
  mensaje que dice qué flag usar.
- `[SEGURO]` **uv se instalaba y el instalador no lo encontraba.** En Debian y
  Ubuntu, `~/.profile` añade `~/.local/bin` al PATH solo si ese directorio ya
  existía al iniciar sesión; en una máquina nueva no existe. El instalador
  descargaba uv, moría con *"uv se instaló pero no está en el PATH"*, y volver a
  correrlo repetía el ciclo entero. Ahora se fija el destino con
  `UV_INSTALL_DIR`, se busca también en `XDG_BIN_HOME` y `~/.cargo/bin`, se
  adopta un uv ya instalado fuera del PATH, y si el instalador de uv falla se
  enseña su salida en vez de taparla.
- `[SEGURO]` **Faltar Docker ya no aborta el instalador, pero tampoco se pasa de
  largo.** El diagnóstico distingue *no instalado*, *sin plugin compose v2* y
  *daemon caído* —tres arreglos distintos—, **recomienda el comando concreto**
  para el caso detectado y explica qué se gana con él (PostgreSQL levantado,
  esquema migrado, administrador sembrado, CSS compilado) frente a lo que
  tocaría hacer a mano. Solo entonces ofrece seguir sin base de datos, y con el
  **«no» por defecto**: si el instalador sabe cuál es la solución, ofrecer la
  salida de emergencia sin recomendarla primero es elegir por quien instala sin
  decírselo. También se comprueba `curl` antes de usarlo.
- `[SEGURO]` El mensaje final pone lo pendiente **antes** de `make dev`, que es
  lo primero que se lee y lo primero que falla sin base de datos.

### Añadido

- `[SEGURO]` Si el instalador falla y hay una terminal delante, espera a que
  pulses Enter antes de salir. Lanzado con doble clic desde el explorador de
  archivos, la ventana se cerraba con el error dentro y el síntoma que llegaba
  era "se cierra solo".
- `[SEGURO]` Job `entornos-hostiles` en el workflow de e2e: locale sin UTF-8,
  stdin cerrado, uv fuera del PATH y una máquina sin Docker. Son fallos que no
  se reproducen en el equipo de quien mantiene el framework.

## [0.2.0] — 2026-09-03 · Auth, correo y seguridad

Un proyecto generado ya sabe quién le está pidiendo las páginas. Registro,
login, sesiones revocables, recuperación de contraseña por correo, y el
endurecimiento que hace que todo eso no sea un juguete.

> **Si vienes de v0.1.0**, salta al final: *Cómo actualizar un proyecto
> existente*. Hay dos pasos manuales, y uno de ellos rompe formularios si se
> omite.

### Autenticación

- `[MIGRACIÓN]` Modelos `User`, `Role`, `UserSession` y `PasswordResetToken`,
  con su migración. Trae también los roles `admin` y `user` sembrados: el código
  los da por hechos, y `require_role("admin")` sobre una tabla vacía no falla —
  niega el acceso a todo el mundo, que es peor.
- `[SEGURO]` Contraseñas con **argon2id**. Nada fuera de `app/security.py`
  hashea ni firma: un solo sitio que auditar.
- `[SEGURO]` **Sesiones revocables**: la cookie lleva un token opaco firmado y
  la tabla guarda solo su SHA-256. Cambiar la contraseña cierra todas las
  sesiones de la cuenta, y rotar `SECRET_KEY` las cierra todas del sitio. Ver
  [ADR-0008](docs/decisions/0008-sesiones-en-base-de-datos.md) para por qué no
  es un JWT.
- `[SEGURO]` Recuperación de contraseña con enlace de un solo uso, hasheado en
  base de datos y con caducidad. Pedir uno nuevo invalida el anterior.
- `[SEGURO]` `CurrentUser`, `OptionalUser` y `require_role(...)` en `app/deps.py`.
  Anónimo → redirección a `/login?next=…`; identificado sin el rol → página 403.
  Son situaciones distintas y no deben colapsar en una: mandar a un formulario
  de login a alguien que ya entró es un bucle del que no sale.
- `[SEGURO]` Las peticiones de HTMX a una página protegida reciben `HX-Redirect`
  en vez de un 303, para que HTMX no incruste la página de login dentro de un
  fragmento.
- `[SEGURO]` **Nunca se revela si un email tiene cuenta.** Contraseña
  incorrecta, dirección desconocida y cuenta desactivada dan el mismo mensaje y
  el mismo tiempo de respuesta —hay un hash señuelo para que el reloj tampoco lo
  cuente—, y `/forgot-password` responde igual exista o no la cuenta.
- `[SEGURO]` `setup.sh` genera `ADMIN_EMAIL` / `ADMIN_PASSWORD`, siembra el
  administrador tras migrar y enseña las credenciales al terminar.
- `[SEGURO]` `ALLOW_REGISTRATION=false` hace que `/register` responda 404, para
  proyectos donde las cuentas las crea un administrador.

### Correo transaccional

- `[SEGURO]` `app/emails/` con `EmailSender` como `Protocol` y cuatro
  adaptadores: `console` (por defecto, imprime en stdout), `resend`, `smtp` y
  uno en memoria para tests, que **no** es seleccionable por `EMAIL_PROVIDER`
  para que un despliegue no pueda tragarse los correos en silencio.
- `[SEGURO]` Plantillas editables en `app/templates/emails/`, dos archivos por
  mensaje (`.html` y `.txt`). **El asunto vive dentro de la plantilla**, en su
  propio bloque: cambiar el texto de un correo no debe obligar a tocar un
  servicio.
- `[SEGURO]` La configuración del proveedor se valida **al arrancar**. Descubrir
  que faltaba `RESEND_API_KEY` en el primer correo de recuperación es un usuario
  encerrado fuera de su cuenta.

### Endurecimiento

- `[RUPTURA]` **CSRF de doble envío**, activo en todas las rutas. Todo
  formulario necesita `{% include "components/csrf_field.html" %}`; sin él, un
  403. HTMX no necesita nada: `base.html` manda el token en `hx-headers`. Ver
  [ADR-0009](docs/decisions/0009-csrf-doble-envio.md).
- `[SEGURO]` **Límites de intentos** en login y recuperación, contados en
  PostgreSQL por IP **y** por cuenta a la vez. En memoria del proceso no valen:
  se vacían en cada despliegue y cada worker lleva el suyo, así que con cuatro
  workers un límite de 10 son 40.
- `[SEGURO]` **Cabeceras de seguridad** en toda respuesta, con la CSP escrita
  como diccionario editable. Lleva `'unsafe-inline'` en `script-src` porque los
  macros de Basecoat traen handlers `onclick`; el porqué y cómo apretarla, en
  [ADR-0010](docs/decisions/0010-cabeceras-de-seguridad-y-csp.md). HSTS solo en
  entorno desplegado.
- `[SEGURO]` **Un identificador por petición**: en `X-Request-ID`, en cada línea
  de log y en la página 500, para que "no me funciona" se convierta en una línea
  concreta que buscar. Sustituye al log de acceso de uvicorn, que se emite fuera
  de la aplicación y por eso no lo lleva.
- `[SEGURO]` Logging estructurado: JSON por línea en entorno desplegado, línea
  legible en local. Lo que pases en `extra={...}` viaja como campos.

### Corregido

Los tres salieron de usar el framework, no de revisarlo.

- `[SEGURO]` **El hook de Alembic solo formateaba, no pasaba el linter.** La
  primera migración de *cualquier* proyecto rompía `make check` nada más
  generarse, por el orden de sus imports. Añadido `ruff check --fix` como hook
  previo en `alembic.ini`.
- `[SEGURO]` **`migrations/env.py` apagaba todos los loggers.** `fileConfig()`
  desactiva por defecto cualquier logger que ya existiera. En los tests dejaba
  mudo el `caplog` de cualquier proyecto; en producción, un proyecto que corra
  `alembic upgrade head` al arrancar pierde TODOS sus logs, sin un error que lo
  explique. Guarda de regresión en `tests/test_database_isolation.py`.
- `[SEGURO]` **El proveedor de correo `console` imprimía sin `flush`.** Con la
  salida redirigida a un archivo, a un gestor de procesos o a un contenedor sin
  `PYTHONUNBUFFERED`, el enlace de recuperación se quedaba en el buffer y
  parecía que no se enviaba nada.

### Infraestructura

- `[SEGURO]` El workflow e2e ahora **corre la suite entera** del proyecto
  generado: levanta PostgreSQL con el propio `setup.sh`, migra, siembra y pasa
  `make check`, además de arrancar la app y comprobar que sirve páginas con sus
  cabeceras. Antes solo pasaba lint y tipos, así que nada de lo que vive en la
  base de datos estaba cubierto.
- `[SEGURO]` Dos dependencias nuevas: `argon2-cffi` y el extra `pydantic[email]`.
  Ninguna trae Node ni rompe [ADR-0005](docs/decisions/0005-sin-nodejs.md). La
  imagen de producción pasa de ~390 a ~400 MB.

### Decisiones registradas

- [0008](docs/decisions/0008-sesiones-en-base-de-datos.md) — sesiones en base de
  datos, no JWT; argon2id para contraseñas.
- [0009](docs/decisions/0009-csrf-doble-envio.md) — CSRF de doble envío,
  validado como dependencia y no como middleware.
- [0010](docs/decisions/0010-cabeceras-de-seguridad-y-csp.md) — cabeceras de
  seguridad, y por qué la CSP lleva `'unsafe-inline'`.

### Cómo actualizar un proyecto existente

1. Trae el código nuevo:

   ```bash
   git checkout upstream/main -- app/security.py app/logs.py app/emails/ \
     app/middleware/ app/models/ app/repositories/ app/services/ app/schemas/ \
     app/routers/auth.py app/deps.py app/templating.py app/main.py \
     app/templates/emails/ app/templates/pages/auth/ \
     app/templates/components/csrf_field.html migrations/env.py alembic.ini
   uv add "argon2-cffi>=23.1" "pydantic[email]>=2.10"
   ```

2. **Migra.** Las tablas nuevas no existen en tu base:

   ```bash
   git checkout upstream/main -- migrations/versions/
   make migrate
   ```

3. **Añade el token CSRF a tus formularios.** Este es el paso que rompe cosas si
   se salta: todo `<form method="post">` que ya tuvieras empezará a recibir un
   403 hasta que lleve dentro
   `{% include "components/csrf_field.html" %}`. Si tu `base.html` está
   personalizado, cópiale también el `hx-headers` del `<body>`.

4. **Declara `user` en tus handlers de página.** `OptionalUser` en las públicas,
   `CurrentUser` en las privadas. Sin eso la cabecera renderiza como si no
   hubiera nadie identificado.

5. Añade al `.env` las variables nuevas (las tienes documentadas en
   `.env.example`) y corre `make seed` para crear el administrador.

6. `make check`.

## [0.1.0] — 2026-09-03 · Esqueleto

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

Todos salieron de construir un catálogo real sobre el framework, no de
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

[0.2.0]: https://github.com/pepeajcu/framework-kiro/releases/tag/v0.2.0
[0.1.0]: https://github.com/pepeajcu/framework-kiro/releases/tag/v0.1.0
