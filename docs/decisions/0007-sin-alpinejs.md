# 0007 — Sin Alpine.js

**Estado:** Aceptada · 2026-09-01
**Revierte:** `docs/framework/vision.md` §3, que incluía Alpine.js en el stack.

## Contexto

El documento de visión contemplaba Alpine.js "solo donde HTMX no alcance":
modales, desplegables, validación instantánea. Era razonable antes de decidir
los componentes.

Con Basecoat adoptado (ADR-0004), el hueco ya está cubierto: sus once
componentes interactivos —acordeón, combobox, diálogo, menú, popover, select,
pestañas, toast y demás— traen su propio JavaScript vanilla.

## Decisión

**No incluir Alpine.js.** La interactividad se reparte entre HTMX (todo lo que
implica al servidor) y el JS vanilla de Basecoat (todo lo puramente visual).

## Consecuencias

- Dos modelos mentales en el cliente en lugar de tres. Menos ocasiones para que
  un agente mezcle `x-data` con `hx-get` y produzca algo que no funciona.
- Menos peso y una dependencia menos que mantener.
- **Es reversible en un minuto**: si aparece un caso real que ni HTMX ni
  Basecoat cubren, se añade el `<script>` de Alpine y se actualiza este ADR. La
  decisión es "no lo añadimos por si acaso", no "está prohibido".
