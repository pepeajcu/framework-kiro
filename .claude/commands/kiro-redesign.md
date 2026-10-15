---
description: Audit an app that already exists against its DESIGN.md and uupm's UX floor, and push variance into it without breaking behaviour; with the argument `auditoría` it only reports, changing nothing
---

# Rediseño de una app existente

Para un proyecto que ya tiene páginas y se parece a todos los demás (mismo gris,
misma cabecera, "tres tarjetas"), o que se construyó antes del motor de diseño.
El objetivo es **cambiar cómo se ve sin cambiar lo que hace**.

## Modo auditoría

Con el argumento `auditoría` haces **solo el punto 1** (el diagnóstico completo) y entregas
el informe: nada se cambia, no hay plan que aprobar. Es la auditoría de UX de toda la app, la
que cubre cada ruta y no solo las que cambiaron. El informe se ordena como el de
`/kiro-design-review`: por la prioridad de uupm, con el id de la regla, ✗, ! o ✓, la
evidencia y dónde se arregla.

## Regla de oro

Todo lo que ya funciona sigue funcionando. `make check` verde antes de empezar
y al terminar. No se cambian rutas, modelos, formularios, el token CSRF
(`components/csrf_field.html`), los atributos de HTMX ni la lógica de sesión de
`partials/nav_auth.html`.

## 1. Diagnostica

1. `make check`. Si no está verde, para y dilo: no se rediseña sobre un proyecto
   roto.
2. Lee `PROJECT.md`, `DESIGN.md` y `design.toml`, y la skill `kiro-design`.
   - Si `DESIGN.md` tiene `TODO`, o `make design-check` dice que `design.toml`
     está en los valores por defecto, **no hay identidad**: corre primero la
     parte de identidad de `/kiro-init` (punto 2) y no sigas hasta tenerla.
3. `make design-check` y apunta cada error y aviso (incluidos los patrones genéricos
   `P1`-`P10` y las skills de diseño rivales `D6`). Para el producto de `PROJECT.md`, pide
   a uupm su guía: `make design-ux q="<el producto>" domain=ux`.
4. Haz el inventario de las páginas (`app/templates/pages/**`, las rutas de
   `app/routers/`) y ordénalas por importancia: portada y las que más ve la gente
   primero.
5. Aplica la auditoría de `.claude/skills/kiro-design/references/redesign.md`
   (tipografía, color, layout, estados, contenido), leída con las reglas de
   `SKILL.md` por encima cuando discrepen (sin CDN, sin imágenes externas, sin
   JS por página).
6. **`make archcheck`.** Lo que antes eran `grep` a mano son reglas con
   número: páginas que extienden `base.html` y partials que extienden (J1),
   formularios POST sin CSRF (J2), colores escritos a mano (J3), clases de Basecoat
   que ya no existen (J4), scripts en línea y recursos externos (J5), más las de
   capas (K1-K8). Cada violación dice archivo, línea y cómo arreglarla. Anótalas
   como parte del inventario; una excepción con motivo (`kiro: allow`) se respeta.
7. Y estas, que una máquina no puede ver:

   | Busca | Cómo |
   |---|---|
   | Cabecera reescrita que perdió la sesión | que `partials/header.html` siga incluyendo `headers/…` y que ninguna cabecera repita el formulario de logout a mano |
   | Fuentes por CDN o `@import` externo | `grep -rn 'fonts.googleapis\|fonts.gstatic\|cdn\.' app/static/css/input.css` (las plantillas ya las cubre J5) |
   | Portada con la forma del ejemplo viejo | titular + badge + rejilla de tarjetas iguales |
   | Misma estructura en todas las secciones | tres bloques imagen+texto seguidos, tres rejillas iguales |
   | Estados que faltan | listas sin vacío, formularios sin error, fetch sin carga |
   | Animación suelta | `@keyframes` propios, `style="animation…"` (los `<script>` en línea ya los cubre J5) |

## 2. Propón

Antes de tocar plantillas, enseña al usuario un plan **corto y ordenado por
impacto**, con lo que vas a cambiar y lo que no:

1. **Identidad** (si falta): paleta, fuentes, tema, cabecera: `design.toml`. Es
   lo de mayor efecto y menor riesgo.
2. **Estructura**: migrar páginas a `layouts/app.html` / `layouts/landing.html`;
   elegir la cabecera.
3. **Portada y las 2-3 páginas clave**, con un arquetipo cada una y la firma visual.
4. **Pulido**: estados, movimiento dentro del nivel del proyecto, responsive.

Espera el visto bueno si el cambio es grande (varias páginas). Si es pequeño y
claro, sigue.

## 3. Ejecuta, por capas

Un paso cada vez, comprobando entre uno y otro:

1. Identidad con los comandos de la skill (`make design-init`, `make brand-colors`,
   `make font`, `make design-set`), luego `make design build`.
2. Migra una página a su layout y comprueba que se ve igual antes de cambiarla.
3. Rediseña la portada con un arquetipo de `references/archetypes.md` y la firma
   visual de `DESIGN.md`.
4. Después, las páginas clave, de una en una.
5. `make css`, `make check`.

Si un test de plantillas falla, es una señal: cambiaste comportamiento sin
querer. Revierte esa parte y vuelve a intentarlo sin tocar la lógica.

## 4. Verifica

Corre `/kiro-design-review` sobre la portada y las páginas rediseñadas (captura
a 375 y 1280 px, comparación con `DESIGN.md`, "¿se parece al default?"). Cierra
con `make design-check` y `make check`.

## 5. Informa

Un resumen corto: qué cambió, qué quedó para otra vuelta (las páginas que no
tocaste, en orden de prioridad) y cualquier decisión que tomaste y el usuario
debería poder revertir. No hagas commit.
