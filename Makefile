# Kiro — comandos del proyecto.
#
# Todo pasa por `uv run`, así que ningún comando depende de que tengas el
# entorno virtual activado. `make help` lista lo disponible.

# Puerto de la app, leído de .env. Cada proyecto usa el suyo para poder
# tener varios corriendo a la vez.
APP_PORT ?= $(shell sed -n 's/^APP_PORT=//p' .env 2>/dev/null | head -1)
APP_PORT := $(or $(APP_PORT),8000)

.DEFAULT_GOAL := help
.PHONY: help dev up down logs ps shell migrate revision migrations-check seed \
	css css-watch lint format types test cov check upgrade clean

# --- Ayuda ------------------------------------------------------------------

help:  ## Mostrar esta ayuda
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "} {printf "  \033[1m%-18s\033[0m %s\n", $$1, $$2}'

# --- Desarrollo -------------------------------------------------------------

dev:  ## Arrancar la app con recarga automática (puerto de APP_PORT en .env)
	uv run uvicorn app.main:app --reload --host 0.0.0.0 --port $(APP_PORT)

up:  ## Levantar los servicios de Docker (PostgreSQL)
	docker compose up -d

down:  ## Parar los servicios de Docker
	docker compose down

logs:  ## Seguir los logs de los contenedores
	docker compose logs -f

ps:  ## Estado de los contenedores
	docker compose ps

shell:  ## Abrir psql contra la base de datos local
	docker compose exec db psql -U $${POSTGRES_USER} -d $${POSTGRES_DB}

# --- Base de datos ----------------------------------------------------------

migrate:  ## Aplicar las migraciones pendientes
	uv run alembic upgrade head

revision:  ## Crear una migración desde los modelos  (make revision m="añade tabla x")
	@test -n "$(m)" || (echo "error: falta el mensaje. Uso: make revision m=\"descripción\"" && exit 1)
	uv run alembic revision --autogenerate -m "$(m)"

migrations-check:  ## Fallar si los modelos cambiaron sin generar migración
	uv run alembic check

seed:  ## Cargar los datos iniciales
	uv run python -m scripts.seed

# --- Frontend (sin Node.js) -------------------------------------------------

css:  ## Compilar Tailwind a app/static/css/app.css
	uv run tailwindcss -i app/static/css/input.css -o app/static/css/app.css --minify

css-watch:  ## Recompilar el CSS al vuelo mientras desarrollas
	uv run tailwindcss -i app/static/css/input.css -o app/static/css/app.css --watch

# --- Calidad ----------------------------------------------------------------

lint:  ## Revisar estilo y errores comunes
	uv run ruff check .
	uv run ruff format --check .

format:  ## Formatear el código y ordenar imports
	uv run ruff format .
	uv run ruff check --fix .

types:  ## Comprobación estática de tipos (el sustituto del compilador)
	uv run mypy app

test:  ## Correr la suite de tests
	uv run pytest

cov:  ## Tests con reporte de cobertura
	uv run pytest --cov --cov-report=term-missing

check: lint types test migrations-check  ## Todo lo anterior. Es lo que corre CI.
# `lint` incluye 'ruff format --check' a propósito: CI lo comprueba, y sin él
# se puede ir en verde en local y en rojo en CI por el formato de un archivo.
	@echo ""
	@echo "  \033[1;32m✓ todo en orden\033[0m"

# --- Mantenimiento ----------------------------------------------------------

upgrade:  ## Ver qué mejoras del framework hay disponibles (requiere remote 'upstream')
	@git remote get-url upstream >/dev/null 2>&1 \
		|| (echo "error: no hay remote 'upstream'. Ver docs/upgrading.md" && exit 1)
	@git fetch upstream --quiet
	@echo "Cambios del framework que tu proyecto todavía no tiene:"
	@echo ""
	@git diff --stat HEAD upstream/main -- app/ scripts/ Dockerfile compose.yml || true
	@echo ""
	@echo "Trae solo lo que quieras:  git checkout upstream/main -- <ruta>"
	@echo "Lee antes el CHANGELOG:    git show upstream/main:CHANGELOG.md | head -60"

clean:  ## Borrar cachés y artefactos de build
	find . -type d -name __pycache__ -prune -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache .mypy_cache .ruff_cache htmlcov .coverage coverage.xml
	rm -f app/static/css/app.css
