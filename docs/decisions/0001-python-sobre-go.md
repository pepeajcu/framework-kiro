# 0001 — Python en vez de Go

**Estado:** Aceptada · 2026-09-01

## Contexto

El objetivo principal del framework es minimizar las alucinaciones de la IA al
generar código. Se evaluaron dos rutas:

- **Go + HTMX + SQLite** — el compilador y el tipado estático real son una
  barrera fuerte contra el código inventado. Un solo binario desplegable.
- **Python + HTMX + PostgreSQL** — tipado dinámico, pero con el ORM más maduro
  del ecosistema (SQLAlchemy 2.0), mucho más material de entrenamiento, y
  familiaridad previa del autor.

## Decisión

**Python 3.12+.** Se prioriza el ORM maduro y la soltura del autor sobre la
garantía de tipado que da un compilador.

La pérdida de seguridad en tiempo de compilación **no se acepta como tal**: se
compensa con tres herramientas que son **obligatorias, no recomendadas**:

- `mypy --strict` sobre `app/`
- Pydantic v2 para validar en tiempo de ejecución
- Ruff como linter

## Consecuencias

- Estas comprobaciones deben estar en pre-commit **y** en CI. A diferencia de
  Go, en Python nada de esto es inherente al lenguaje: si no está forzado en el
  flujo, no existe. Ese es el punto frágil de esta decisión y donde hay que
  vigilar.
- `mypy --strict` desde el primer commit, no como limpieza posterior: adoptarlo
  tarde sobre un código ya escrito es mucho más caro.
- PostgreSQL en vez de SQLite implica Docker en desarrollo. Se acepta a cambio
  de concurrencia de escritura real.
