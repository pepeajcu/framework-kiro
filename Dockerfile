# syntax=docker/dockerfile:1
#
# Imagen multi-etapa. Sin Node.js en ninguna etapa: Tailwind se compila con su
# CLI standalone, gestionado desde Python (ver docs/decisions/0005-sin-nodejs.md).
#
#   docker build --target development .   entorno de desarrollo
#   docker build --target production  .   imagen de despliegue (la de por defecto)

# ---------------------------------------------------------------------------
# base — intérprete y gestor de paquetes, comunes a todas las etapas
# ---------------------------------------------------------------------------
FROM python:3.12-slim-bookworm AS base

# uv se copia desde su imagen oficial en vez de instalarse con curl: es más
# rápido, reproducible, y no necesita red en el build.
COPY --from=ghcr.io/astral-sh/uv:0.12.8 /uv /uvx /bin/

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /srv

# ---------------------------------------------------------------------------
# deps — dependencias de producción
#
# Se copian solo los manifiestos antes del código: mientras no cambien, Docker
# reutiliza esta capa y el build no reinstala nada.
# ---------------------------------------------------------------------------
FROM base AS deps

COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project

# ---------------------------------------------------------------------------
# deps-dev — añade las herramientas de desarrollo (ruff, mypy, pytest, tailwind)
# ---------------------------------------------------------------------------
FROM deps AS deps-dev

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project

# ---------------------------------------------------------------------------
# assets — sincroniza design.toml en input.css y compila el CSS
#
# En su propia etapa para que el binario de Tailwind y los fuentes de CSS no
# acaben en la imagen final: solo viajan los estáticos compilados.
# ---------------------------------------------------------------------------
FROM deps-dev AS assets

COPY design.toml ./design.toml
COPY app ./app
COPY scripts ./scripts
RUN python -m scripts.design build \
    && tailwindcss -i app/static/css/input.css -o app/static/css/app.css --minify

# ---------------------------------------------------------------------------
# development — recarga en caliente; el código se monta como volumen
# ---------------------------------------------------------------------------
FROM deps-dev AS development

COPY . .
COPY --from=assets /srv/app/static/css/app.css ./app/static/css/app.css

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# ---------------------------------------------------------------------------
# production — imagen final, mínima y sin privilegios
# ---------------------------------------------------------------------------
FROM base AS production

# Usuario sin privilegios: si alguien consigue ejecución dentro del contenedor,
# no es root. Se crea antes de copiar para que las capas queden cacheadas.
RUN groupadd --system --gid 1001 app \
    && useradd --system --uid 1001 --gid app --no-create-home app

COPY --from=deps --chown=app:app /opt/venv /opt/venv
COPY --chown=app:app alembic.ini ./
COPY --chown=app:app migrations ./migrations
COPY --chown=app:app app ./app
# design.toml también viaja: las plantillas leen de ahí la cabecera, la
# superficie oscura y los scripts de motion (app/design_engine/runtime.py). Sin
# él, producción se vería con los valores por defecto.
COPY --chown=app:app design.toml ./design.toml
# scripts/ viaja a producción: el `CMD` ejecuta `python -m scripts.seed` al arrancar,
# igual que las migraciones. Son unos pocos KB.
COPY --chown=app:app scripts ./scripts
COPY --from=assets --chown=app:app /srv/app/static ./app/static

USER app
EXPOSE 8000

# Redes privadas de Docker/Coolify/Traefik/Nginx confiables para X-Forwarded-For.
# Sobrescribible como variable de entorno en el panel de despliegue.
ENV FORWARDED_ALLOW_IPS="127.0.0.1,::1,10.0.0.0/8,172.16.0.0/12,192.168.0.0/16"

# Sin curl en la imagen slim: se usa el propio Python, que ya está.
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=4).status == 200 else 1)"

# Antes de servir tráfico aplica las migraciones y refresca el seed. Ambas son
# idempotentes, así que cada despliegue deja la base al día sin pasos manuales; si fallan,
# el contenedor no arranca y el error sale en los Logs (ADR-0024). Con más de una réplica,
# mover la migración a un paso previo al despliegue (docs/deploy-coolify.md, §4).
# Un solo proceso por contenedor: escalar es responsabilidad del orquestador,
# que es quien sabe cuánta CPU hay. Varios workers dentro de un contenedor
# esconden el uso real de recursos al panel de despliegue.
CMD ["sh", "-c", "alembic upgrade head && python -m scripts.seed && exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips \"${FORWARDED_ALLOW_IPS}\""]
