# Kiro Framework — Documentación de Proyecto

> **Kiro** — framework/boilerplate propio basado en **P**ython + **HTM**X + **S**QL(PostgreSQL) + **A**lchemy (SQLAlchemy).

Este documento es la fuente de verdad del proyecto. Está escrito para que una IA (Claude Code, OpenCode, u otro agente) lo lea antes de empezar a construir, y para servir como base de un `CLAUDE.md` / `PROJECT.md` dentro del propio repo una vez creado.

---

## 1. Qué es esto y por qué existe

José (autor y único desarrollador por ahora) dirige **GainWeb**, una agencia de desarrollo y administración web en Guatemala, y tiene proyectos propios (ej. una app de planificación de bodas — "Wedding Planner"). El objetivo de Kiro es tener un **framework/boilerplate propio, reutilizable vía `git clone`**, que:

1. Ahorre tiempo y tokens de IA al iniciar cada proyecto nuevo (nada de reconstruir arquitectura, Docker, auth, etc. desde cero cada vez).
2. Minimice las alucinaciones de la IA al generar código, gracias a un stack con tipado fuerte, convenciones explícitas y un archivo de instrucciones (`CLAUDE.md`) que fija reglas claras.
3. Sirva como base para arrancar **cualquier tipo de proyecto**: sitios web, ecommerce, landing pages, apps, web apps, ideas nuevas que se quieran desarrollar y probar rápido — ya sea para tener un MVP veloz o algo más elaborado pero bien construido desde el inicio.
4. Sea compatible con **Claude Code** y **OpenCode**, incluyendo las skills favoritas de Claude Code que José ya usa.

Kiro está pensado como la base por defecto para arrancar cualquier proyecto nuevo (propio o de cliente de GainWeb) que tenga algo de lógica de negocio, sin importar qué tan simple o compleja sea esa lógica al inicio.

---

## 2. Decisión de stack: por qué Python y no Go

Se evaluaron dos rutas antes de decidir:

- **Go + HTMX + SQLite**: mayor garantía contra alucinaciones de IA (compilador estricto, tipado fuerte real, SQLite de archivo único sin servidor que configurar). Ventajas: menor superficie de error, testing local trivial, un solo binario desplegable.
- **Python + HTMX + PostgreSQL**: menor garantía de tipado "duro" que Go (Python es de tipado dinámico por naturaleza), pero se puede compensar significativamente con herramientas. Ventajas: ORM mucho más maduro y potente (SQLAlchemy 2.0), José ya tiene soltura en Python (lo usa a diario en su trabajo de analítica), más ejemplos de entrenamiento para la IA en este ecosistema, PostgreSQL es más robusto que SQLite para concurrencia de escritura en apps multi-tenant con más tráfico.

**Decisión final: Python.** Se prioriza el ORM maduro (SQLAlchemy) y la comodidad de José sobre la garantía extra de tipado que da Go. La pérdida de "seguridad de tipos en compilación" se compensa con:

- **mypy** o **pyright** (chequeo estático de tipos) — integrado a CI, no opcional.
- **Pydantic v2** (validación de datos en tiempo de ejecución, explota inmediatamente si un campo no existe o no coincide con el tipo esperado).
- **Ruff** (linter rápido, combina varios chequeos de estilo y errores comunes).

Nota importante: a diferencia de Go, estas protecciones en Python **no son inherentes al lenguaje** — dependen de que estén integradas de forma obligatoria en el flujo de desarrollo (pre-commit hooks, CI). Esto debe quedar resuelto desde la v1.0.0, no como "buena práctica opcional".

---

## 3. Stack técnico definitivo

| Capa | Tecnología | Notas |
|---|---|---|
| Lenguaje | Python 3.12+ | Con type hints obligatorios |
| Framework web | FastAPI | Genera OpenAPI automático, ayuda a que la IA "vea" los tipos de los endpoints |
| Base de datos | PostgreSQL | Vía Docker Compose, `sslmode=require` cuando sea remoto |
| ORM | SQLAlchemy 2.0 (no Django ORM, no Django) | El más potente y maduro del ecosistema Python; soporta patrón "Core" (SQL casi puro tipado) y ORM completo |
| Migraciones | Alembic | Mismo autor que SQLAlchemy, integración nativa |
| Validación de datos | Pydantic v2 | Schemas de entrada/salida en cada endpoint |
| Chequeo estático de tipos | mypy o pyright | Obligatorio en CI, no opcional |
| Linter | Ruff | Rápido, combina varios chequeos |
| Frontend / interactividad | HTMX | Servidor devuelve fragmentos HTML, no JSON; minimiza JS custom escrito a mano |
| Reactividad ligera en cliente | Alpine.js | Solo donde HTMX no alcance (toggles, modales, validación instantánea) |
| Templates / SSR | Jinja2 | Server-side rendering puro, sin hidratación |
| Componentes UI | shadcn/ui (adaptado a HTML/Jinja2/Tailwind) | Ver sección 5 |
| Testing | pytest | — |
| Contenedores | Docker + Docker Compose | Postgres + app, listo para levantar en local o producción |

### Por qué HTMX y no React/Vue/Next.js

HTMX **es** JavaScript (14kb), pero la ventaja real es que José nunca escribe ese JavaScript a mano. En vez de `fetch()`, manejo de promesas y actualización manual del DOM (toda esa superficie es donde más alucina la IA), HTMX resuelve el patrón "clic → petición al servidor → actualizar parte de la página" de forma declarativa en atributos HTML (`hx-get`, `hx-post`, `hx-target`, `hx-swap`, `hx-trigger`).

Frente a Next.js específicamente: Next con App Router mezcla server components, client components, streaming y server actions — ahí es donde más alucina la IA por la ambigüedad de "¿esto es server o client?". El stack Kiro es SSR de principio a fin, siempre, sin excepciones — sin esa ambigüedad.

### SSR (server-side rendering) siempre — prioridad SEO

El flujo es: request → FastAPI consulta PostgreSQL vía SQLAlchemy → renderiza plantilla Jinja2 con esos datos → HTML completo enviado al navegador. Esto es SSR puro, y es una regla de arquitectura, no una opción: **toda página de Kiro se renderiza en servidor, sin excepción**, precisamente porque el SEO es una prioridad constante en los proyectos de José (catálogos, landing pages, sitios de clientes que necesitan ser indexados bien por Google).

HTMX no reemplaza esto — lo complementa: la carga inicial es SSR completo, y cada interacción posterior también devuelve HTML (fragmentos) renderizado en servidor. Nunca hay salto a renderizado en cliente, nunca hay contenido que dependa de JavaScript para ser visible a un crawler.

---

## 4. Estructura de carpetas del repo

```
kiro-framework/
├── setup.sh                    # script interactivo de configuración inicial
├── docker-compose.yml          # Postgres + app, listo para levantar
├── Dockerfile
├── .env.example
├── CLAUDE.md                   # instrucciones para Claude Code (fuente de verdad)
├── AGENTS.md                   # para OpenCode — symlink o referencia a CLAUDE.md
├── PROJECT.md                  # explica el proyecto específico a la IA (template vacío al clonar)
├── app/
│   ├── main.py
│   ├── models/                 # SQLAlchemy models
│   ├── schemas/                # Pydantic schemas
│   ├── routers/                # endpoints organizados por dominio
│   ├── auth/                   # módulo de autenticación (ver sección 6)
│   ├── emails/                 # plantillas y configuración de envío de correo (ver sección 6)
│   ├── templates/
│   │   ├── partials/           # fragmentos HTMX
│   │   └── components/         # componentes tipo shadcn/ui adaptados a Jinja2
│   └── static/
├── migrations/                 # Alembic
├── tests/
├── .claude/
│   ├── skills/                 # skills favoritas de José, heredadas por cada proyecto clonado
│   │   └── tu-skill/SKILL.md
│   └── commands/                # slash commands custom
└── docs/
    └── decisions.md             # ADRs — decisiones de arquitectura tomadas
```

---

## 5. shadcn/ui como base de componentes visuales

Para cualquier desarrollo que no tenga especificaciones gráficas propias (proyectos internos, MVPs rápidos, prototipos) o para dashboards internos/admin, Kiro debe apoyarse en los componentes y el sistema de diseño de **shadcn/ui** como base visual por defecto.

- shadcn/ui está pensado originalmente para React, así que en Kiro se adapta como una librería de **componentes HTML + Tailwind CSS** (misma filosofía de diseño: componentes copiables y personalizables, no una dependencia de paquete cerrada) usados dentro de las plantillas Jinja2.
- Esto da una base visual consistente y profesional sin que José tenga que diseñar desde cero cada proyecto nuevo o cada dashboard.
- Cuando un proyecto sí tenga especificaciones gráficas de marca (branding propio de un cliente), shadcn/ui se usa solo como esqueleto estructural y se sobreescribe con la identidad visual correspondiente.

---

## 6. Módulo de autenticación y correo — desde la v1.0.0

A diferencia de lo planteado originalmente, el módulo de **Auth** no se deja para una versión posterior: se construye **desde la primera versión**, porque prácticamente todo proyecto que use Kiro (ecommerce, dashboards, apps con usuarios) lo necesita de entrada.

### Auth incluye desde v1.0.0:

- Registro y login con email y contraseña.
- Contraseñas **hasheadas** (bcrypt o argon2 — nunca texto plano ni hashes débiles).
- Flujo de **recuperación de contraseña** (solicitud → email con enlace firmado de un solo uso → formulario de nueva contraseña).
- Sesiones por cookie firmada.
- Estructura de permisos/roles básica, pensada para reutilizarse en distintos tipos de proyecto (ej. admin vs. usuario final).

### Envío de correo — resuelto vía servicio de terceros, configurable desde el framework

El envío de correo (necesario para recuperación de contraseña, y en general para cualquier notificación transaccional) **no se resuelve montando un servidor de correo propio** — eso implica gestionar reputación de IP, SPF/DKIM/DMARC, listas negras, etc., que no vale la pena para este tipo de proyectos.

En vez de eso, Kiro se conecta a un **servicio de terceros de envío de correo transaccional vía API** (ej. Resend, Postmark, u otro similar — a decidir por costo/volumen en su momento), y dentro del propio framework se deja:

- La integración ya lista (cliente/wrapper en Python para llamar a la API del proveedor elegido).
- Las credenciales del proveedor como variables de entorno (`.env`), configurables por proyecto.
- Un sistema de **plantillas de correo editable desde el propio framework** (carpeta `app/emails/`), para que los mensajes (bienvenida, recuperación de contraseña, confirmaciones) se puedan personalizar por proyecto sin tocar la lógica de envío.

---

## 7. El script de setup (`setup.sh`)

Debe sentirse como un instalador real, no un git clone pasivo. Flujo esperado:

1. Pregunta interactiva por terminal: nombre del proyecto, descripción corta, si necesita módulo de ecommerce/pagos (Auth ya viene incluido siempre, ver sección 6).
2. Genera `.env` con valores random seguros (secrets, passwords de DB, placeholders para credenciales del proveedor de correo).
3. Genera `PROJECT.md` rellenado con las respuestas dadas.
4. Renombra referencias en `docker-compose.yml` según el nombre del proyecto.
5. Corre `docker compose up -d` para levantar Postgres.
6. Corre las migraciones iniciales de Alembic (incluyendo las tablas de usuarios/auth).
7. Mensaje final confirmando que el proyecto está listo para `docker compose up`.

Objetivo: que la IA (o José) entre directo a construir features del negocio, sin gastar el primer tramo de la sesión generando boilerplate desde cero.

---

## 8. CLAUDE.md — contenido esperado

Este archivo vive en la raíz de cada proyecto generado desde Kiro y es la pieza clave para evitar alucinaciones. Debe incluir, como mínimo:

- **Stack fijo** (no cambiar sin aprobación explícita): FastAPI + Python 3.12, PostgreSQL vía SQLAlchemy 2.0 (async) + Alembic, Pydantic v2, Jinja2 + HTMX + Alpine.js (solo donde haga falta), shadcn/ui como base de componentes, pytest.
- **Instrucción de leer siempre `PROJECT.md`** antes de escribir código — ahí está el contexto específico del proyecto (entidades, reglas de negocio, decisiones ya tomadas).
- **Convenciones obligatorias**:
  - Toda query a DB pasa por una capa de `repositories/` (nunca SQLAlchemy directo en routers).
  - Todo endpoint tiene su Pydantic schema de entrada/salida.
  - Todo modelo nuevo requiere su migración Alembic correspondiente.
  - Nombres de archivos en snake_case.
  - Fragmentos HTMX van en `templates/partials/`.
  - Toda página se renderiza server-side (SSR), sin excepción — regla de arquitectura, no sugerencia.
- **Comandos comunes**: `docker compose up`, `alembic revision --autogenerate -m "mensaje"`, `pytest`.
- **Qué NO hacer**: no usar Django ni Flask (el proyecto usa FastAPI), no usar React/Vue para nada (HTMX only), no instalar ORMs alternativos, no montar servidor de correo propio (usar el proveedor de terceros ya configurado).

## 9. PROJECT.md — contenido esperado (template)

Archivo que cambia por cada proyecto/cliente. Estructura:

```markdown
# PROJECT.md

## Qué es este proyecto
[Descripción de negocio]

## Entidades principales
[Modelos y sus campos clave]

## Reglas de negocio específicas
[Ej. "El stock no puede ir negativo", reglas de expiración, etc.]

## Decisiones ya tomadas (no reabrir sin razón)
[Ej. "Se decidió NO usar carrito persistente, es sesión simple"]
```

## 10. Compatibilidad Claude Code + OpenCode

Ambas herramientas leen archivos de instrucciones en la raíz del repo, con nombres de archivo distintos según la herramienta. Solución: `CLAUDE.md` es la única fuente de verdad; `AGENTS.md` es un symlink (o un archivo que simplemente redirige: "lee CLAUDE.md") para evitar duplicar contenido que se desincroniza con el tiempo.

**Pendiente de verificar**: confirmar el nombre exacto de archivo que espera OpenCode antes de fijarlo en el template — la convención puede cambiar entre versiones de la herramienta.

## 11. Skills de Claude Code

Las skills favoritas de José deben vivir en `.claude/skills/` dentro del propio boilerplate, para que cada proyecto clonado las herede automáticamente sin tener que configurarlas de nuevo cada vez.

---

## 12. Analítica y marketing — por qué van en el core, no como añadido

Dado el perfil de José (analista de marketing/eCommerce, GA4/BigQuery en su trabajo diario), esto es una ventaja competitiva real del stack: Kiro puede hacer **tracking server-side nativo**, algo que Next.js/React normalmente resuelven solo con paquetes de terceros que viven 100% en el cliente (bloqueables por ad-blockers).

### Debe incluir desde la v1.0.0:

- **GTM (Google Tag Manager)**: contenedor base en `<head>`/`<body>` del template Jinja2 raíz, ID como variable de entorno (`GTM_ID`) — cada proyecto solo cambia el `.env`, no el código.
- **GA4**: normalmente vía GTM, pero dejar también la opción de **Measurement Protocol server-side** — enviar eventos críticos (compra confirmada, formulario enviado) directo desde Python a GA4, sin depender del navegador ni de que el JS cargue.
- **Google Search Console**: placeholder de verificación (meta tag o archivo HTML) en el template, para no olvidarlo por proyecto.
- **Facebook Pixel + Conversions API**: Pixel en cliente vía GTM + Conversions API server-side en Python para eventos que deben llegar garantizados (lo que Meta empuja desde que iOS 14 rompió el tracking solo-cliente).
- **robots.txt + sitemap.xml dinámico**: generado desde las rutas/productos reales de la base de datos, no estático.
- **Open Graph + meta tags**: template base con bloques Jinja2 sobreescribibles por página (título, descripción, imagen) — para que compartir en WhatsApp/redes se vea bien.
- **Banner de consentimiento de cookies**: simple (HTMX + cookie propia, sin librerías pesadas), para verse profesional aunque Guatemala no tenga ley tipo GDPR.

---

## 13. Alcance de la v1.0.0

La versión 1.0.0 del framework debe, como mínimo:

- Generar, al clonar y correr `setup.sh`, una página de inicio funcional con un "Hola Mundo" de bienvenida a Kiro.
- Tener Docker Compose funcional con PostgreSQL.
- Tener el `CLAUDE.md` y `PROJECT.md` (template) ya en su lugar.
- Tener la estructura de carpetas base descrita en la sección 4.
- Incluir la configuración de analítica/marketing descrita en la sección 12 (al menos como placeholders configurables por `.env`).
- Incluir el **módulo de Auth completo** descrito en la sección 6: registro/login con email y contraseña hasheada, recuperación de contraseña, sesiones, y la integración con el servicio de correo de terceros ya configurada (con plantillas editables).
- Incluir **shadcn/ui** (adaptado a HTML/Jinja2/Tailwind) como base de componentes visuales por defecto, descrito en la sección 5.
- Garantizar que **toda página se renderiza vía SSR** desde el primer commit — no es un ajuste posterior, es la arquitectura base, por prioridad de SEO.
