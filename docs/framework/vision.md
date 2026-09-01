# Documento de visión original

> **Qué es esto.** El documento de partida del framework, escrito antes de
> existir una sola línea de código. Se conserva como registro de intención: por
> qué se eligió cada pieza y qué problema se quería resolver.
>
> **No es documentación vigente.** Varias decisiones cambiaron al construirlo, y
> siempre mandan los [ADRs](../decisions/). En concreto:
>
> | Dice aquí | Vigente | Motivo |
> |---|---|---|
> | SQLAlchemy async (§8) | **Síncrono** | [ADR-0002](../decisions/0002-sqlalchemy-sincrono.md) |
> | Alpine.js en el stack (§3) | **Sin Alpine** | [ADR-0007](../decisions/0007-sin-alpinejs.md) |
> | Adaptar shadcn/ui a mano (§5) | **Basecoat vendorizado** | [ADR-0004](../decisions/0004-basecoat-en-vez-de-portar-shadcn.md) |
> | `CLAUDE.md` como fuente de verdad (§10) | **`AGENTS.md`** | Estándar abierto; `CLAUDE.md` lo importa |
> | Sin gestor de paquetes definido | **uv** | No se contemplaba en su momento |
>
> Para saber cómo está construido el framework hoy, lee
> [`../architecture.md`](../architecture.md).

---

## 1. Qué es esto y por qué existe

El framework nace de una situación repetida: arrancar varios proyectos web al
año —propios y de cliente— y empezar cada uno reconstruyendo lo mismo.
Arquitectura, Docker, autenticación, convenciones. Ese tramo inicial no aporta
nada al negocio del proyecto y, cuando se hace con ayuda de una IA, es además
donde más se equivoca el modelo: está inventando decisiones en lugar de
seguirlas.

El objetivo es un boilerplate propio, reutilizable vía `git clone`, que:

1. Ahorre tiempo y tokens al iniciar cada proyecto nuevo.
2. Minimice las alucinaciones de la IA al generar código, mediante un stack con
   tipado fuerte, convenciones explícitas y un archivo de instrucciones que fija
   reglas claras.
3. Sirva de base para **cualquier tipo de proyecto**: sitios web, ecommerce,
   landing pages, aplicaciones web, ideas nuevas que se quieran probar rápido —
   ya sea para un MVP veloz o para algo más elaborado pero bien construido desde
   el inicio.
4. Sea compatible con Claude Code y OpenCode, incluidas las skills que ya se
   usen habitualmente.

Está pensado como la base por defecto de cualquier proyecto nuevo que tenga algo
de lógica de negocio, sin importar cuán simple o compleja sea al principio.

---

## 2. Decisión de stack: por qué Python y no Go

Se evaluaron dos rutas antes de decidir:

- **Go + HTMX + SQLite**: mayor garantía contra alucinaciones (compilador
  estricto, tipado fuerte real, SQLite de archivo único sin servidor que
  configurar). Ventajas: menor superficie de error, testing local trivial, un
  solo binario desplegable.
- **Python + HTMX + PostgreSQL**: menor garantía de tipado "duro" que Go, pero
  compensable con herramientas. Ventajas: ORM mucho más maduro y potente
  (SQLAlchemy 2.0), familiaridad previa con el lenguaje, más ejemplos de
  entrenamiento para la IA en este ecosistema, y PostgreSQL como base más robusta
  que SQLite para concurrencia de escritura.

**Decisión final: Python.** Se prioriza el ORM maduro y la comodidad de quien
va a escribir el código sobre la garantía extra de tipado que da Go. La pérdida
de seguridad de tipos en compilación se compensa con:

- **mypy** o **pyright** (chequeo estático de tipos), integrado a CI, no opcional.
- **Pydantic v2** (validación en tiempo de ejecución: falla de inmediato si un
  campo no existe o no coincide con el tipo esperado).
- **Ruff** (linter rápido que combina varios chequeos de estilo y errores comunes).

Nota importante: a diferencia de Go, estas protecciones **no son inherentes al
lenguaje** — dependen de estar integradas de forma obligatoria en el flujo de
desarrollo (pre-commit, CI). Debe quedar resuelto desde la v1.0.0, no como
"buena práctica opcional".

---

## 3. Stack técnico definitivo

| Capa | Tecnología | Notas |
|---|---|---|
| Lenguaje | Python 3.12+ | Con type hints obligatorios |
| Framework web | FastAPI | Genera OpenAPI automático, ayuda a que la IA "vea" los tipos de los endpoints |
| Base de datos | PostgreSQL | Vía Docker Compose, `sslmode=require` cuando sea remoto |
| ORM | SQLAlchemy 2.0 (no Django ORM, no Django) | El más maduro del ecosistema Python; soporta patrón "Core" (SQL casi puro tipado) y ORM completo |
| Migraciones | Alembic | Mismo autor que SQLAlchemy, integración nativa |
| Validación de datos | Pydantic v2 | Schemas de entrada/salida en cada endpoint |
| Chequeo estático de tipos | mypy o pyright | Obligatorio en CI, no opcional |
| Linter | Ruff | Rápido, combina varios chequeos |
| Frontend / interactividad | HTMX | El servidor devuelve fragmentos HTML, no JSON; minimiza el JS escrito a mano |
| Reactividad ligera en cliente | Alpine.js | *(Descartado — ver [ADR-0007](../decisions/0007-sin-alpinejs.md))* |
| Templates / SSR | Jinja2 | Renderizado en servidor puro, sin hidratación |
| Componentes UI | shadcn/ui adaptado | *(Resuelto con Basecoat — ver [ADR-0004](../decisions/0004-basecoat-en-vez-de-portar-shadcn.md))* |
| Testing | pytest | — |
| Contenedores | Docker + Docker Compose | Postgres + app, listo para levantar en local o producción |

### Por qué HTMX y no React/Vue/Next.js

HTMX **es** JavaScript (14 kb), pero la ventaja real es que ese JavaScript no se
escribe a mano. En vez de `fetch()`, manejo de promesas y actualización manual
del DOM —toda esa superficie es donde más alucina la IA— HTMX resuelve el patrón
"clic → petición al servidor → actualizar parte de la página" de forma
declarativa, en atributos HTML (`hx-get`, `hx-post`, `hx-target`, `hx-swap`,
`hx-trigger`).

Frente a Next.js en concreto: su App Router mezcla server components, client
components, streaming y server actions. Ahí es donde más alucina la IA, por la
ambigüedad de "¿esto es servidor o cliente?". Este stack es SSR de principio a
fin, siempre, sin esa ambigüedad.

### SSR siempre — prioridad SEO

El flujo es: petición → FastAPI consulta PostgreSQL vía SQLAlchemy → renderiza
plantilla Jinja2 con esos datos → HTML completo enviado al navegador. Esto es
SSR puro, y es una regla de arquitectura, no una opción: **toda página se
renderiza en servidor, sin excepción**, porque el SEO es una prioridad constante
en el tipo de proyectos a los que sirve este framework (catálogos, landing
pages, sitios que necesitan indexarse bien).

HTMX no reemplaza esto, lo complementa: la carga inicial es SSR completo, y cada
interacción posterior también devuelve HTML renderizado en servidor. Nunca hay
salto a renderizado en cliente, nunca hay contenido que dependa de JavaScript
para ser visible a un crawler.

---

## 4. Estructura de carpetas del repo

```
kiro-framework/
├── setup.sh                    # script interactivo de configuración inicial
├── docker-compose.yml          # Postgres + app, listo para levantar
├── Dockerfile
├── .env.example
├── CLAUDE.md                   # instrucciones para Claude Code
├── AGENTS.md                   # para OpenCode
├── PROJECT.md                  # explica el proyecto específico a la IA
├── app/
│   ├── main.py
│   ├── models/                 # SQLAlchemy models
│   ├── schemas/                # Pydantic schemas
│   ├── routers/                # endpoints organizados por dominio
│   ├── auth/                   # módulo de autenticación (ver sección 6)
│   ├── emails/                 # plantillas y envío de correo (ver sección 6)
│   ├── templates/
│   │   ├── partials/           # fragmentos HTMX
│   │   └── components/         # componentes tipo shadcn/ui en Jinja2
│   └── static/
├── migrations/                 # Alembic
├── tests/
├── .claude/
│   ├── skills/                 # skills heredadas por cada proyecto clonado
│   └── commands/               # slash commands custom
└── docs/
    └── decisions.md            # ADRs
```

---

## 5. shadcn/ui como base de componentes visuales

Para cualquier desarrollo sin especificaciones gráficas propias (proyectos
internos, MVPs, prototipos) o para dashboards de administración, el framework
debe apoyarse en los componentes y el sistema de diseño de **shadcn/ui** como
base visual por defecto.

- shadcn/ui está pensado originalmente para React, así que aquí se adapta como
  una librería de **componentes HTML + Tailwind CSS** —misma filosofía de
  diseño: componentes copiables y personalizables, no una dependencia cerrada—
  usados dentro de las plantillas Jinja2.
- Esto da una base visual consistente y profesional sin tener que diseñar desde
  cero cada proyecto o cada dashboard.
- Cuando un proyecto sí tenga identidad de marca propia, shadcn/ui se usa solo
  como esqueleto estructural y se sobreescribe con esa identidad.

---

## 6. Módulo de autenticación y correo — desde la v1.0.0

A diferencia de lo planteado en un primer momento, el módulo de **Auth** no se
deja para una versión posterior: se construye **desde la primera versión**,
porque prácticamente todo proyecto que use el framework (ecommerce, dashboards,
aplicaciones con usuarios) lo necesita de entrada.

### Auth incluye desde v1.0.0

- Registro y login con email y contraseña.
- Contraseñas **hasheadas** (bcrypt o argon2 — nunca texto plano ni hashes débiles).
- Flujo de **recuperación de contraseña** (solicitud → email con enlace firmado
  de un solo uso → formulario de nueva contraseña).
- Sesiones por cookie firmada.
- Estructura de permisos/roles básica, reutilizable entre tipos de proyecto
  (por ejemplo, administrador frente a usuario final).

### Envío de correo — vía servicio de terceros, configurable

El envío de correo (necesario para recuperación de contraseña y, en general,
para cualquier notificación transaccional) **no se resuelve montando un servidor
de correo propio**: eso implica gestionar reputación de IP, SPF/DKIM/DMARC y
listas negras, que no compensa para este tipo de proyectos.

En su lugar, el framework se conecta a un **servicio de terceros de correo
transaccional vía API** (Resend, Postmark u otro similar, a decidir por coste y
volumen), y dentro del propio framework se deja:

- La integración lista (cliente o wrapper en Python para llamar a la API).
- Las credenciales como variables de entorno, configurables por proyecto.
- Un sistema de **plantillas de correo editables desde el framework**
  (`app/emails/`), para personalizar los mensajes por proyecto sin tocar la
  lógica de envío.

---

## 7. El script de setup (`setup.sh`)

Debe sentirse como un instalador real, no un `git clone` pasivo. Flujo esperado:

1. Preguntas por terminal: nombre del proyecto, descripción corta, si necesita
   módulo de ecommerce/pagos (Auth va siempre incluido, ver sección 6).
2. Genera `.env` con valores aleatorios seguros (secretos, contraseña de base de
   datos, placeholders para el proveedor de correo).
3. Genera `PROJECT.md` rellenado con las respuestas.
4. Renombra las referencias en `docker-compose.yml` según el nombre del proyecto.
5. Levanta Postgres con `docker compose up -d`.
6. Corre las migraciones iniciales de Alembic, incluidas las tablas de usuarios.
7. Mensaje final confirmando que el proyecto está listo.

Objetivo: que la IA —o la persona— entre directo a construir funcionalidad de
negocio, sin gastar el primer tramo de la sesión generando boilerplate.

---

## 8. CLAUDE.md — contenido esperado

Vive en la raíz de cada proyecto generado y es la pieza clave para evitar
alucinaciones. Debe incluir, como mínimo:

- **Stack fijo** (no cambiar sin aprobación explícita): FastAPI + Python 3.12,
  PostgreSQL vía SQLAlchemy 2.0 + Alembic, Pydantic v2, Jinja2 + HTMX,
  shadcn/ui como base de componentes, pytest.
- **Instrucción de leer siempre `PROJECT.md`** antes de escribir código: ahí está
  el contexto específico del proyecto (entidades, reglas de negocio, decisiones
  ya tomadas).
- **Convenciones obligatorias**:
  - Toda consulta a base de datos pasa por una capa de `repositories/`; nunca
    SQLAlchemy directo en los routers.
  - Todo endpoint tiene su schema Pydantic de entrada y salida.
  - Todo modelo nuevo requiere su migración de Alembic.
  - Nombres de archivo en snake_case.
  - Los fragmentos HTMX van en `templates/partials/`.
  - Toda página se renderiza en servidor, sin excepción: es regla de
    arquitectura, no sugerencia.
- **Comandos comunes**: levantar el entorno, generar migraciones, correr tests.
- **Qué NO hacer**: no usar Django ni Flask; no usar React ni Vue para nada; no
  instalar ORMs alternativos; no montar servidor de correo propio.

---

## 9. PROJECT.md — contenido esperado (plantilla)

Archivo que cambia con cada proyecto. Estructura:

```markdown
# PROJECT.md

## Qué es este proyecto
[Descripción de negocio]

## Entidades principales
[Modelos y sus campos clave]

## Reglas de negocio específicas
[Por ejemplo: "el stock no puede quedar negativo", reglas de expiración…]

## Decisiones ya tomadas (no reabrir sin razón)
[Por ejemplo: "se decidió NO usar carrito persistente; es sesión simple"]
```

---

## 10. Compatibilidad Claude Code + OpenCode

Ambas herramientas leen archivos de instrucciones en la raíz del repositorio,
con nombres distintos según la herramienta. Solución: una única fuente de
verdad, y que el otro archivo apunte a ella, para evitar duplicar contenido que
se desincroniza con el tiempo.

*Pendiente en su momento: confirmar el nombre exacto que espera OpenCode. Se
resolvió a favor de `AGENTS.md` como archivo canónico, con `CLAUDE.md`
importándolo.*

---

## 11. Skills de Claude Code

Las skills habituales deben vivir en `.claude/skills/` dentro del propio
boilerplate, para que cada proyecto clonado las herede sin configurarlas de
nuevo.

---

## 12. Analítica y marketing — por qué van en el core, no como añadido

Este stack puede hacer **tracking desde el servidor**, algo que React y Next.js
normalmente resuelven solo con paquetes de terceros que viven al 100 % en el
cliente y que cualquier bloqueador de anuncios desactiva. Es una ventaja real y
por eso forma parte del núcleo, no de un añadido posterior.

### Debe incluir desde la v1.0.0

- **Google Tag Manager**: contenedor base en la plantilla Jinja2 raíz, con el ID
  como variable de entorno. Cada proyecto solo cambia su configuración, no el
  código.
- **GA4**: normalmente vía GTM, pero dejando también la opción de **Measurement
  Protocol desde el servidor** — enviar eventos críticos (compra confirmada,
  formulario enviado) directamente desde Python, sin depender del navegador ni
  de que cargue el JavaScript.
- **Google Search Console**: placeholder de verificación en la plantilla, para
  no olvidarlo en cada proyecto.
- **Meta Pixel + Conversions API**: pixel en cliente vía GTM, y Conversions API
  desde el servidor para los eventos que deben llegar garantizados.
- **`robots.txt` y `sitemap.xml` dinámico**: generado desde las rutas y los
  registros reales de la base de datos, no estático.
- **Open Graph y meta tags**: plantilla base con bloques sobreescribibles por
  página (título, descripción, imagen), para que compartir el enlace se vea bien.
- **Banner de consentimiento de cookies**: simple, con HTMX y una cookie propia,
  sin librerías pesadas.

---

## 13. Alcance de la v1.0.0

La versión 1.0.0 debe, como mínimo:

- Generar, al clonar y correr `setup.sh`, una página de inicio funcional.
- Tener Docker Compose funcional con PostgreSQL.
- Tener los archivos de instrucciones para la IA en su lugar.
- Tener la estructura de carpetas de la sección 4.
- Incluir la configuración de analítica y SEO de la sección 12, al menos como
  placeholders configurables por variables de entorno.
- Incluir el **módulo de Auth completo** de la sección 6: registro y login con
  contraseña hasheada, recuperación de contraseña, sesiones, y la integración
  con el servicio de correo ya configurada, con plantillas editables.
- Incluir la base de componentes visuales descrita en la sección 5.
- Garantizar que **toda página se renderiza en servidor** desde el primer
  commit: no es un ajuste posterior, es la arquitectura base, por prioridad
  de SEO.
