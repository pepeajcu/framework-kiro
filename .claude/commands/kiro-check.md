---
description: Run the full quality gate and fix what fails
---

# Comprobación completa

Corre `make check`. Ejecuta lint, tipos, tests y detección de migraciones
pendientes — es exactamente lo que corre CI.

Si algo falla, arréglalo y vuelve a correrlo hasta que pase. Por orden de
prioridad:

1. **Tipos** (`mypy --strict`) — en este stack sustituye al compilador. Un fallo
   de tipos casi siempre es un bug real, no ruido. No lo silencies con
   `# type: ignore` sin explicar en un comentario por qué es correcto.
2. **Tests** — si un test falla, entiende por qué antes de tocarlo. Cambiar el
   test para que pase es la forma más rápida de esconder un bug.
3. **Migraciones** — si `alembic check` detecta cambios, falta generar una
   migración: `make revision m="..."`.
4. **Lint** — `make format` arregla la mayoría automáticamente.

Al terminar, di qué falló y qué hiciste. Si algo no se pudo arreglar, dilo
explícitamente en vez de dar el trabajo por terminado.
