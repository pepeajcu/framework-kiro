# Kiro

**Un framework para arrancar proyectos web con IA sin gastar la primera hora
explicándole la arquitectura.**

Clonas, corres `./setup.sh`, y tienes una aplicación funcionando con Postgres,
componentes, Docker y —lo importante— un archivo de instrucciones que le dice al
agente cuál es el stack, cómo se organiza el código y qué no debe tocar.

```bash
git clone https://github.com/pepeajcu/framework-kiro.git mi-proyecto
cd mi-proyecto
./setup.sh
```

---

## Por qué existe

Cada sesión nueva con una IA empieza igual: reconstruir la arquitectura,
configurar Docker, decidir dónde van las queries, explicar las convenciones. Ese
tramo inicial es además donde más alucina el modelo, porque está inventando
decisiones en vez de seguirlas.

Kiro llega con esas decisiones ya tomadas y escritas donde el agente las lee:

- **`AGENTS.md`** — el stack, las capas, las reglas duras y lo que está
  prohibido. Formato abierto: lo leen Claude Code, OpenCode, Codex y Cursor.
- **`PROJECT.md`** — tu dominio de negocio. Lo rellenas una vez y deja de
  inventarse tus entidades.
- **`.claude/skills/`** — el camino exacto para añadir una feature, con código
  real del propio repositorio.

## El stack

| Capa | Elección |
|---|---|
| Lenguaje | Python 3.12+ con tipado obligatorio (`mypy --strict`) |
| Web | FastAPI, renderizado en servidor de principio a fin |
| Base de datos | PostgreSQL · SQLAlchemy 2.0 **síncrono** · Alembic |
| Frontend | Jinja2 + HTMX + [Basecoat](https://basecoatui.com) (shadcn/ui en HTML) |
| CSS | Tailwind v4 vía CLI standalone — **cero Node.js** |
| Contenedores | Docker multi-etapa, sin privilegios, listo para Coolify/Dokploy |

Cada elección está justificada en [`docs/decisions/`](docs/decisions/). Varias
contradicen lo que un modelo asumiría por defecto, y esa es justamente la razón
de escribirlas:

- **SQLAlchemy síncrono, no async** — es donde más alucina la IA en este stack, y
  con SSR el cuello de botella no es la concurrencia
  ([ADR-0002](docs/decisions/0002-sqlalchemy-sincrono.md)).
- **Sin Node.js** — un solo toolchain, un solo gestor de paquetes
  ([ADR-0005](docs/decisions/0005-sin-nodejs.md)).
- **Sin Alpine.js** — HTMX y el JS de Basecoat ya lo cubren; un tercer paradigma
  solo añade confusión ([ADR-0007](docs/decisions/0007-sin-alpinejs.md)).
- **Sesiones en base de datos, no JWT** — un token autocontenido no se puede
  revocar, así que cambiar la contraseña no echa a quien te la robó
  ([ADR-0008](docs/decisions/0008-sesiones-en-base-de-datos.md)).

## Qué trae hecho

- Instalador interactivo que genera secretos, **detecta puertos libres** y deja
  la base de datos migrada, sembrada y corriendo — con tu cuenta de
  administrador ya creada.
- **Autenticación completa**: registro, login con argon2id, sesiones revocables,
  roles y recuperación de contraseña por correo. Ningún formulario revela si un
  email tiene cuenta.
- **Correo transaccional** con tres proveedores intercambiables (consola, Resend,
  SMTP) y plantillas que editas sin tocar código.
- **Endurecido de serie**: CSRF en todas las rutas, límites de intentos
  respaldados por PostgreSQL, cabeceras de seguridad y un identificador por
  petición en cada línea de log.
- SSR completo con SEO de serie: canonical, Open Graph, páginas 404/500 propias.
- Capa de repositorios tipada que hace cumplible la regla "ninguna query fuera
  de `repositories/`".
- Alembic con convención de nombres de constraints, para que las migraciones
  autogeneradas sean revisables.
- Suite de tests con base de datos aislada y rollback por test.
- `make check`: lint + tipos + tests + detección de migraciones pendientes.
- CI que **genera un proyecto desde cero y corre su suite** — lo único que
  impide que el instalador se pudra en silencio.

## Estado

En desarrollo activo. Ver [`CHANGELOG.md`](CHANGELOG.md) y el
[roadmap](docs/framework/roadmap.md).

| Versión | Contenido | Estado |
|---|---|---|
| v0.1.0 | Esqueleto: Docker, SSR, componentes, capa IA, CI | Publicada |
| v0.2.0 | Auth, correo transaccional, CSRF y seguridad | Publicada |
| v0.3.0 | Analítica server-side y SEO | Pendiente |
| v1.0.0 | Documentación, ejemplo completo, release público | Pendiente |

## Documentación

- [Primeros pasos](docs/getting-started.md)
- [Arquitectura](docs/architecture.md)
- [Desplegar en Coolify](docs/deploy-coolify.md)
- [Actualizar un proyecto existente](docs/upgrading.md)
- [Dependencias vendorizadas](docs/vendor.md)
- [Decisiones de arquitectura](docs/decisions/)

## Nota sobre el nombre

"Kiro" es también el IDE agéntico de AWS. La colisión está reconocida y
documentada en [ADR-0006](docs/decisions/0006-nombre-kiro.md); el nombre está
contenido en un punto único para poder cambiarlo antes de un lanzamiento
público.

## Licencia

MIT — ver [`LICENSE`](LICENSE).
