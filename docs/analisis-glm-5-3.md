# Análisis del framework: por qué todas las apps se parecen y cómo diversificar el diseño

> Análisis de `z-ai/glm-5.3` (vía opencode) · 2026-10-12
> Estado del framework en el momento del análisis: ADR-0013 ya aplicada
> (`DESIGN.md`, `make brand-colors`, `make logo`, skill `kiro-design` con
> taste-skill vendorizado, `/kiro-init` existente en `.claude/commands/`).

Se revisaron: `.claude/skills/kiro-design/SKILL.md` y sus `references/`,
`.claude/commands/kiro-init.md`, `DESIGN.md`, `docs/decisions/0013-*`,
`app/static/css/input.css`, los temas vendorizados de Basecoat,
`app/templates/` (`base.html`, `partials/header.html`, `pages/home.html`) y el
`Makefile`.

## Conclusión en una línea

El mecanismo de identidad de Kiro funciona, pero solo cambia la **pintura**
(tokens: color, radio, fuente, logo) y nunca la **arquitectura** (estructura de
página). taste-skill no "falló": es que sus estilos más expresivos son los que
menos especificación tienen, y sus reglas anti-slop son deliberadamente
conservadoras. Dos apps con distinto acento de color siguen leyéndose como el
mismo diseño.

## Causas raíz

### 1. La identidad vive solo en tokens

ADR-0013 y `kiro-design/SKILL.md:60-73` canalizan toda la identidad hacia
`make brand-colors` (`--primary`, `--ring`), `--radius`, `--font-sans` y
`brand_logo()`. Nada de eso toca la composición: el header, el hero, la
retícula de tarjetas y el footer son siempre los mismos bloques. Cambiar tokens
sin cambiar estructura produce variaciones que el ojo percibe como triviales.

### 2. Las reglas anti-slop son conservadoras por diseño

`kiro-design/SKILL.md:87-148`: un solo acento, saturación bajo 80%, sin
gradientes ni glow, tipografía contenida, hero que cabe en el primer viewport.
La propia skill dice *"Break them only when `DESIGN.md` says so"* (línea 89). Si
el brief no empuja varianza explícitamente, la IA converge siempre al punto
medio seguro. Las reglas evitan el slop, pero también frenan lo experimental.

### 3. Los presets expresivos son los que menos receta tienen

De los 6 presets (`kiro-design/SKILL.md:43-50`), solo 3 tienen referencia
vendorizada (`minimalist.md`, `soft.md`, `brutalist.md`). `expresivo`
(9/8/3, "agency, creative, consumer launch"), `institucional` y
`panel-de-datos` se definen solo con dials. Es decir: el preset que se necesita
para un diseño atractivo y único es el único sin guía concreta, así que la IA
cae de vuelta al Basecoat sobrio con acento distinto.

### 4. Cuatro de seis presets son de baja varianza

`minimalista` (5/3/2), `suave-premium` (7/6/3), `institucional` (3/2/5) y
`panel-de-datos` (3/2/8) apuntan a sobrio. `/kiro-init` recomienda según el
público y casi siempre empuja hacia ahí. Solo `brutalista` (9/4/6) y
`expresivo` (9/8/3) son atrevidos, y uno de ellos es el sin-referencia del
punto 3.

### 5. La fuente (el mayor diferenciador) es un paso manual

`kiro-design/SKILL.md:75-86` pide descargar el `.woff2`, declarar
`@font-face` en `input.css` y apuntar `--font-sans` en `@theme`. No existe
`make font`. Si nadie hace ese paso manual en cada proyecto, todo se queda en
la fuente por defecto y la mitad del carácter visual se pierde.

### 6. Motion > 4 exige pedir permiso, así que no existe

`kiro-design/SKILL.md:150-155`: por encima de MOTION_INTENSITY 4 hay que
"preguntar antes de vendorizar una librería". Resultado en la práctica: no se
vendoriza nada, todo queda estático y el resultado se lee igual de plano en los
siete proyectos.

### 7. Los 8 temas de Basecoat son variaciones sutiles del mismo shadcn

`input.css:10-12` permite cambiar vega/nova/maia/lyra/mira/luma/sera/rhea, pero
los ocho comparten estructura: cambia el matiz, no el lenguaje visual. Cambiar
de tema no es cambiar de diseño.

## Propuestas

| # | Propuesta | Dónde aterrizaría | Impacto |
|---|---|---|---|
| 1 | **Arquetipos de página**: 5-6 esqueletos estructurales (split-screen, sidebar-app, editorial/bento, big-type poster, dashboard denso, landing centrada) como snippets Jinja+Tailwind que respetan la CSP (sin CDN). `/kiro-init` pregunta el arquetipo y la IA deja de generar siempre hero + tarjetas | `kiro-design/references/archetypes/` + skill | Máximo: cambia la arquitectura, no la pintura |
| 2 | **Referencia real para `expresivo`** (y para `institucional` y `panel-de-datos`): receta concreta con tipografía display, composición asimétrica, glow/gradientes *con intención*, overlays de ruido | `references/expresivo.md` etc. | Alto: es el preset pedido para "diseño atractivo y único" |
| 3 | **Presets nuevos atrevidos**: `editorial-revista` (serif display, columnas, tipo enorme), `neon-tech` (dark-first, acento luminoso), `retro-terminal` (CRT, mono). Con receta completa, no solo dials | `kiro-design` | Alto, junto con 2 |
| 4 | **`make font name=...`**: descarga el woff2 de Fontsource, escribe el `@font-face` y apunta `--font-display`/`--font-sans` automáticamente | `Makefile` + script | Alto y barato: elimina la fricción del punto 5 |
| 5 | **Kit de efectos CSS/vanilla**: revelados con IntersectionObserver, marquee, spotlight, grano/ruido, scanlines, sombras duras. Recetario por preset, siempre con `prefers-reduced-motion` | `input.css` + skill | El "wow"; sin CDN y sin Node, viable con CSS puro |
| 6 | **Overrides de componentes por estilo**: packs en `app/templates/components/` (botón brutalista con sombra dura y borde 2px, cards glass para expresivo) y variantes de header (full-bleed, centrado, sidebar; hoy `header.html:3` es sticky-blur para todos) | `components/` | Medio-alto: coherencia dentro de cada estilo |
| 7 | **`/kiro-redesign`**: audita una app existente contra `DESIGN.md` y empuja varianza a propósito (adaptación del `redesign-skill` de taste-skill upstream) | nuevo command | Medio: rescata las 7 apps ya construidas |
| 8 | **Defaults por preset**: cada preset fija automáticamente tema de Basecoat, radio, fuente sugerida y paleta, para que incluso un relleno perezoso dé variedad | skill + `/kiro-init` | Medio: variedad de serie |

Notas adicionales:

- El upstream de taste-skill también tiene `image-to-code-skill` e
  `imagegen-frontend-web` (comps visuales de referencia antes de codificar).
  Adaptar el flujo "referencia visual primero, código después" a `/kiro-init`
  (aunque sea pidiendo URLs de sitios de referencia, sin generación de
  imágenes) ancla cada proyecto a un look concreto y lejos del default.
- Las restricciones que NO se deberían tocar para lograr esto: CSP sin CDN,
  sin Node.js (ADR-0005), contraste WCAG y `prefers-reduced-motion`. Todo lo
  propuesto es CSS puro, JS vanilla vendorizado o Jinja.

## Orden recomendado

1. **Propuestas 1, 2 y 4 juntas**: cambian lo que de verdad se ve (estructura,
   receta del estilo expresivo, tipografía con carácter).
2. **5 y 6**: el acabado memorable (efectos y componentes por estilo).
3. **7**: rescate de las aplicaciones ya construidas.
4. **3 y 8**: amortizan el trabajo en cada proyecto futuro.
