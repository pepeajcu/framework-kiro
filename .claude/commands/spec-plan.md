---
description: Compact one-stop spec for medium features — writes plan.md (requirements + design + tasks) before /spec-build
---

# Plan compacto de especificación: $ARGUMENTS

Este es el camino intermedio entre usar la skill `kiro-feature` directamente
(cambios pequeños, cero ceremonia) y el flujo completo de tres paradas
(`/spec-new` → `/spec-design` → `/spec-tasks`, reservado para features grandes o
con alta incertidumbre). Genera **un único documento** (`plan.md`) y pide **una
sola aprobación** antes de `/spec-build`.

## Pasos

1. Lee `PROJECT.md` y el código existente que se vaya a tocar o reutilizar. Si
   falta una decisión de dominio crítica, **pregunta al usuario antes de
   escribir el plan**.

2. Elige el siguiente correlativo de tres dígitos en `docs/specs/` y crea
   `docs/specs/NNN-<slug>/plan.md` con esta estructura:

```markdown
# NNN — <Título>

## Problema
Qué resuelve y para quién, en 2-4 frases.

## Requisitos verificables
- **R1 — <Nombre>:** CUANDO <situación>, EL SISTEMA DEBE <comportamiento observable y testeable>.
- **R2 — <Nombre>:** ...

## Capas y reutilización
- **Modelo / Migración:** tablas o columnas nuevas (`app/models/...`).
- **Repositorio:** consultas necesarias (`app/repositories/...`).
- **Schema / Servicio:** validaciones y reglas de negocio (`app/schemas/...`, `app/services/...`).
- **Router / Plantillas:** rutas SSR y fragmentos HTMX (`app/routers/...`, `app/templates/...`).
- **Reutilización:** qué piezas existentes se aprovechan.

## Tareas (orden del Golden Path)
- [ ] 1. <Tarea de modelo + migración> — Archivos: ... — Cubre: R1 — Hecho cuando: `make migrations-check`
- [ ] 2. <Tarea de repositorio / schema / servicio> — Archivos: ... — Cubre: R1
- [ ] 3. <Tarea de router + plantillas + `make css`> — Archivos: ... — Cubre: R1, R2
- [ ] 4. <Tests de integración> — Archivos: `tests/test_...py` — Cubre: R1, R2
- [ ] 5. Puerta de calidad completa — Hecho cuando: `make check` pasa en verde
```

3. Verifica que el plan cumple las reglas de `AGENTS.md` (SSR, SQL solo en
   repositorios, escrituras vía servicio, `OptionalUser`/`CurrentUser` en
   páginas, CSRF en formularios POST).

4. Muestra el resumen al usuario y **espera su aprobación en esta única parada**.
   Cuando apruebe, ejecuta con `/spec-build`.
