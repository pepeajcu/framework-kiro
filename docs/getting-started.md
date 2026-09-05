# Primeros pasos

## Requisitos

- Docker con el plugin `compose` v2
- Python 3.12+
- git

`setup.sh` comprueba todo esto antes de tocar nada, e instala `uv` si falta.

## Crear un proyecto

```bash
git clone https://github.com/pepeajcu/framework-kiro.git mi-proyecto
cd mi-proyecto
./setup.sh
```

El instalador pregunta el nombre, el slug, la descripción, el dominio, el
proveedor de correo y los puertos. Los valores por defecto de los puertos son el
**primer puerto libre** que encuentra, no el canónico: si ya tienes otro Postgres
en el 5432, Kiro usa el 5433 sin que tengas que enterarte.

Después genera `.env` con secretos aleatorios, personaliza los archivos, levanta
PostgreSQL, aplica las migraciones y compila el CSS.

### Modo no interactivo

Útil para scripts y CI:

```bash
./setup.sh --non-interactive \
  --name "Mi Proyecto" \
  --description "Descripción corta del proyecto" \
  --domain midominio.com \
  --email-provider resend
```

`./setup.sh --help` lista todas las opciones.

### Historial de git

El instalador pregunta qué hacer con el historial:

- **`fresh`** — borra el historial de Kiro y empieza limpio. Lo normal.
- **`upstream`** — conserva Kiro como remote `upstream`, lo que habilita
  `make upgrade` para traer mejoras del framework más adelante. Ver
  [actualizar](upgrading.md).
- **`keep`** — no toca git.

## El día a día

```bash
make dev        # arrancar con recarga automática
make check      # lint + tipos + tests + migraciones — antes de cada commit
make help       # todos los comandos
```

Instala los hooks de pre-commit una vez por clon:

```bash
uv run pre-commit install
```

## Antes de pedirle la primera feature a la IA

Abre Claude Code u OpenCode en el proyecto y corre `/kiro-init`. Te entrevista
para rellenar `PROJECT.md` (entidades, reglas de negocio, decisiones ya
tomadas — es lo que el agente lee para no inventarse tu dominio) y te explica
las dos formas de pedir una feature a partir de ahí:

- **Golden path directo** — para un cambio normal: lo pides tal cual y el
  agente sigue solo las 8 capas del golden path (`kiro-feature`).
- **Desarrollo acompañado** — para una feature grande o con requisitos
  ambiguos: `/spec-new` → `/spec-design` → `/spec-tasks` → `/spec-build`, cada
  uno esperando tu aprobación antes de seguir al siguiente.

## Problemas frecuentes

**El puerto ya está ocupado** — cambia `POSTGRES_PORT` o `APP_PORT` en `.env`.
Con varios proyectos en la misma máquina es lo habitual.

**`uv sync --frozen` falla con "Missing workspace member"** — el `uv.lock` no
corresponde al nombre del proyecto. Corre `uv lock`.

**El CSS no refleja mis cambios** — `make css`. Tailwind solo emite las clases
que encuentra en las plantillas; una clase nueva no existe hasta recompilar.

**PostgreSQL arranca en bucle** — si vienes de una versión anterior del volumen,
bórralo: `docker compose down -v`. PostgreSQL 18 cambió el punto de montaje.
