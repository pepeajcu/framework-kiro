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
	css css-watch logo brand-colors font motion design design-build design-watch design-init \
	design-set design-check design-propose design-apply design-reference design-brief-schema design-advise design-ux vendor-uupm archcheck lint format types test cov audit check upgrade clean

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

logo:  ## Importar el logo de la marca  (make logo src=./logo.svg  o una URL; SVG o PNG 1:1)
	@test -n "$(src)" || (echo "error: falta src. Uso: make logo src=./logo.svg" && exit 1)
	uv run python -m scripts.brand logo "$(src)"

brand-colors:  ## Aplicar el color de marca  (make brand-colors primary="#0F766E" [radius=0.5rem] [neutral=warm] [surface=cream] [secondary="#hex"])
	@test -n "$(primary)" || (echo "error: falta primary. Uso: make brand-colors primary=\"#0F766E\"" && exit 1)
	uv run python -m scripts.brand colors --primary "$(primary)" $(if $(radius),--radius "$(radius)") $(if $(neutral),--neutral "$(neutral)") $(if $(surface),--surface "$(surface)") $(if $(secondary),--secondary "$(secondary)")
	$(MAKE) css

font:  ## Añadir una fuente local  (make font name="Fraunces" weights="400,700" role=display)
	@test -n "$(name)" -a -n "$(role)" || (echo "error: faltan name y role. Uso: make font name=\"Fraunces\" weights=\"400,700\" role=display" && exit 1)
	uv run python -m scripts.font --name "$(name)" --weights "$(or $(weights),400)" --role "$(role)" $(if $(fallback),--fallback "$(fallback)")
	$(MAKE) css

css-watch:  ## Recompilar el CSS al vuelo mientras desarrollas
	uv run tailwindcss -i app/static/css/input.css -o app/static/css/app.css --watch

motion:  ## Vendorizar la librería de un nivel de motion  (make motion level=motion|gsap)
	@test "$(level)" = "motion" -o "$(level)" = "gsap" || (echo "error: level debe ser motion o gsap. Uso: make motion level=gsap" && exit 1)
	uv run python -m scripts.motion --level "$(level)"

# --- Motor de diseño ---------------------------------------------------------
#
# design.toml es el contrato de la identidad; `make design build` lo compila a
# CSS, fuentes y motion. Se puede escribir `make design build` o `make design-build`.

DESIGN_WORDS := build watch init set check propose apply advise ux
ifneq ($(filter design,$(MAKECMDGOALS)),)
# `make design build`: la segunda palabra es el subcomando, no una meta aparte.
$(filter $(DESIGN_WORDS),$(MAKECMDGOALS)): ; @:
endif

design:  ## Motor de diseño: make design build | watch | init | set | check | propose | apply | advise | ux
	@$(MAKE) --no-print-directory design-$(or $(firstword $(filter $(DESIGN_WORDS),$(MAKECMDGOALS))),build)

design-build:  ## Aplicar design.toml: CSS, fuentes y motion. Idempotente
	uv run python -m scripts.design build
	$(MAKE) css

design-watch:  ## Recompilar al cambiar design.toml (junto a `make css-watch`)
	uv run python -m scripts.design watch

design-init:  ## Crear design.toml desde un estilo  (make design-init preset=brutalista [primary="#DC2626"] [force=1])
	uv run python -m scripts.design init $(if $(preset),--preset "$(preset)") $(if $(primary),--primary "$(primary)") $(if $(force),--force)
	$(MAKE) css

design-set:  ## Cambiar valores del contrato  (make design-set v="basecoat.theme=rhea motion.level=6")
	@test -n "$(v)" || (echo "error: falta v. Uso: make design-set v=\"motion.level=6\"" && exit 1)
	uv run python -m scripts.design set $(v)
	$(MAKE) css

design-propose:  ## Traducir un brief a una propuesta  (make design-propose from=brief.json [base=base.json] [name=spa] [fonts=fuentes.json])
	uv run python -m scripts.design propose $(if $(from),--from "$(from)") $(if $(base),--base "$(base)") $(if $(name),--name "$(name)") $(if $(fonts),--fonts "$(fonts)")

design-advise:  ## Pedir a uupm un sistema de diseño para el producto y proponerlo  (make design-advise q="landing de un spa de lujo" [name=spa])
	@test -n "$(q)" || (echo "error: falta q. Uso: make design-advise q=\"landing de un spa de lujo\"" && exit 1)
	uv run python -m scripts.design advise "$(q)" $(if $(name),--name "$(name)")

design-ux:  ## Consultar una guía de uupm  (make design-ux q="formularios y errores" [domain=ux|chart|landing|style|color|typography|product] [stack=1])
	@test -n "$(q)" || (echo "error: falta q. Uso: make design-ux q=\"formularios y errores\"" && exit 1)
	uv run python -m scripts.design ux "$(q)" $(if $(domain),--domain "$(domain)") $(if $(stack),--stack)

vendor-uupm:  ## (mantenedores) Traer el asesor uupm fijado y reconstruir su solapamiento
	uv run python -m scripts.vendor_uupm

design-reference:  ## Tomar el lenguaje visual de una referencia  (make design-reference url=https://... | md=style.md | skillui=https://... | skillui_dir=carpeta  [name=x] [base=brief.json])
	@test -n "$(url)$(md)$(skillui)$(skillui_dir)" || (echo "error: falta url, md, skillui o skillui_dir. Uso: make design-reference url=https://ejemplo.com" && exit 1)
	uv run python -m scripts.reference $(if $(url),--url "$(url)") $(if $(md),--md "$(md)") $(if $(skillui),--skillui "$(skillui)") $(if $(skillui_dir),--skillui-dir "$(skillui_dir)") $(if $(name),--name "$(name)") $(if $(base),--base "$(base)") $(if $(mode),--mode "$(mode)")

design-brief-schema:  ## Imprimir el esquema JSON de un brief (para rellenarlo desde un texto libre)
	uv run python -m scripts.design schema

design-apply:  ## Aplicar una propuesta guardada en .design/proposals/  (make design-apply proposal=spa [force=1])
	@test -n "$(proposal)" || (echo "error: falta proposal. Uso: make design-apply proposal=spa" && exit 1)
	uv run python -m scripts.design apply "$(proposal)" $(if $(force),--force)
	$(MAKE) css

design-check:  ## Validar design.toml contra el proyecto (`make check` lo corre con allow_defaults=1)
	uv run python -m scripts.design check $(if $(allow_defaults),--allow-defaults)

# --- Calidad ----------------------------------------------------------------

lint:  ## Revisar estilo y errores comunes
	uv run ruff check .
	uv run ruff format --check .

format:  ## Formatear el código y ordenar imports
	uv run ruff format .
	uv run ruff check --fix .

archcheck:  ## Reglas de arquitectura de AGENTS.md (K1-K8, J1-J5); `make archcheck rules=1` las lista
	uv run python -m scripts.archcheck $(if $(rules),--rules)

types:  ## Comprobación estática de tipos (el sustituto del compilador)
	uv run mypy app scripts/archcheck.py

test:  ## Correr la suite de tests
	uv run pytest

cov:  ## Tests con reporte de cobertura
	uv run pytest --cov --cov-report=term-missing

audit:  ## Buscar vulnerabilidades conocidas en las dependencias
	uv run pip-audit

# Lo que corre CI es esto mismo (más `pip-audit` y la imagen de Docker): una sola
# definición de "en verde", para que no se pueda estar en verde aquí y en rojo allí.
# `lint` incluye 'ruff format --check' a propósito, y `css` porque un Tailwind que
# falla deja la app arrancando sin estilos. El contrato de diseño va con
# allow_defaults=1: un proyecto recién clonado todavía no tiene identidad (eso lo
# resuelve /kiro-init y lo avisa el check), pero un contrato roto, un input.css
# desfasado o una fuente que falta sí rompen.
check:  ## Lint + tipos + css + diseño + arquitectura + tests + migraciones. Es lo que corre CI.
	@$(MAKE) --no-print-directory lint types css archcheck test migrations-check
	@$(MAKE) --no-print-directory design-check allow_defaults=1
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
