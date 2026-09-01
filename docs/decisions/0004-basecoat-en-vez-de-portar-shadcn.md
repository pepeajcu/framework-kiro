# 0004 — Adoptar Basecoat en vez de portar shadcn/ui a Jinja2

**Estado:** Aceptada · 2026-09-01

## Contexto

El documento de visión (§5) planteaba adaptar shadcn/ui a componentes
HTML + Tailwind usables desde plantillas Jinja2. shadcn/ui está construido sobre
React y Radix, así que "adaptarlo" significaba reescribir a mano cada componente
y su comportamiento accesible: semanas de trabajo, y una superficie enorme de
mantenimiento propio.

[Basecoat](https://basecoatui.com) ya es exactamente eso: el sistema de diseño
de shadcn/ui implementado en HTML + Tailwind + JavaScript vanilla, licencia MIT,
más de 45 componentes, compatible con los temas de shadcn/ui — y **distribuye
macros de Jinja2**, pensadas explícitamente para copiarse al proyecto y editarse
allí.

## Decisión

**Adoptar Basecoat**, copiando sus macros Jinja y su CSS al repositorio
(*vendoring*), no consumiéndolo como dependencia.

## Consecuencias

- El trabajo pasa de "reescribir shadcn/ui" a "copiar y elegir tema".
- El *vendoring* mantiene la filosofía de shadcn intacta: los componentes son
  del proyecto y se editan sin pelear con una dependencia.
- Contrapartida: las mejoras de Basecoat no llegan solas. `docs/` documenta de
  qué versión se copió y cómo actualizarla.
- Los componentes vendorizados viven en `app/templates/basecoat/` y **están
  excluidos de la sustitución de tokens** de `setup.sh` — ver ADR-0005 y
  `scripts/lib/replace.sh`.
