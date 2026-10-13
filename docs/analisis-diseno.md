# Kiro: que cada proyecto tenga un diseño propio

> **Estado:** análisis y propuestas, 2026-10-12. Todavía no se ha implementado
> nada; las fases de abajo están pendientes de decidir.

## Contexto

Con el commit `78bab4a` (taste-skill + `DESIGN.md`) los proyectos ya cambian de
color y de radio, pero siguen pareciéndose: siete apps, siete variaciones del
mismo shadcn minimalista. El problema no es la skill de taste, es que **el
framework neutraliza casi todo lo que la skill propone**. Revisé el código y
estas son las causas, de mayor a menor peso.

### Diagnóstico: por qué todo sale igual

1. **Solo cambian 3 tokens de ~20.** `app/branding.py:brand_tokens` escribe
   `--primary`, `--primary-foreground` y `--ring` (y `--radius`). El fondo,
   texto, `card`, `muted`, `border`, `secondary`, `accent` se quedan en el gris
   neutro de Basecoat. `DESIGN.md` pregunta "neutros cálidos/fríos" pero nada
   lo aplica. Resultado: la misma app gris con otro color de botón.
2. **El esqueleto HTML está fijo y la IA lo copia.**
   - `app/templates/base.html:87` mete todo en `<main class="mx-auto max-w-5xl px-4 py-10">`:
     ninguna página puede ir a sangre completa, ni tener un hero que ocupe la pantalla.
   - `partials/header.html` (sticky + blur + logo a la izquierda + botones ghost)
     y `partials/footer.html` (una línea de copyright) se heredan siempre; la IA
     casi nunca los reescribe.
   - `pages/home.html` (badge + h1 + 2 cards) y el ejemplo de `kiro-feature`
     (`grid sm:grid-cols-2` de `card`) son los "ejemplos vivos": la IA los imita.
3. **El tema de Basecoat siempre es `vega`.** Hay 8 (`sera` es de radio 0,
   `luma/maia/rhea` redondeados…), la skill lo menciona pero `/kiro-init` nunca
   elige uno.
4. **No hay tipografías.** `app/static/fonts/` ni existe. Vendorizar una fuente
   es un paso manual de 3 pasos; la IA lo salta y sale la fuente del sistema. La
   tipografía display es lo que más diferencia visualmente un sitio.
5. **La skill resumida es casi solo prohibiciones.** `kiro-design/SKILL.md` dice
   "si discrepan, este archivo gana", y lo que gana es restrictivo: un acento,
   saturación < 80 %, "no serif", 2 familias × 2 pesos, cards solo si hace
   falta, motion casi nulo ("pregunta antes de vendorizar"). Contradice incluso
   a `references/minimalist.md`, que pide serif editorial. Reglas de *qué no
   hacer* sin reglas de *qué sí hacer* convergen siempre al minimalismo seguro.
6. **Se perdió la parte generativa de taste-skill.** El original (89 KB) tiene
   el "Creative Variance Engine" (arquetipos de layout y textura que se
   sortean), §4.8 imágenes ("ni un sitio minimalista es solo texto; el hero
   necesita un visual real"), §5 esqueletos de scroll (sticky-stack,
   horizontal-pan) y las definiciones de los diales. Tampoco están
   `redesign-skill` (auditar y subir de nivel una página existente) ni `brandkit`.
7. **Los presets convergen.** 6 estilos, solo 3 con referencia, y `expresivo`
   (el más experimental) no tiene ninguna. El usuario elige de una lista, y la
   lista misma está sesgada a lo sobrio.
8. **La IA nunca ve lo que diseña.** `/kiro-init` paso 5 dice "dile que abra la
   portada". Sin captura de pantalla no hay iteración, y el primer borrador
   (el más genérico) es el que se queda.

## Propuesta (en orden de impacto / esfuerzo)

### Fase 1 — Quitar los homogeneizadores (alto impacto, bajo esfuerzo)

- **Layouts en vez de un `main` fijo.** `base.html` deja el contenedor en un
  bloque (`{% block main %}`) y se añaden dos layouts:
  `layouts/app.html` (el `max-w-5xl` actual, para pantallas privadas) y
  `layouts/landing.html` (a sangre completa, secciones propias). Las páginas
  existentes extienden `layouts/app.html`; nada se rompe.
- **Header y footer como parte de la identidad.** `kiro-design` exige
  reescribirlos al aplicar el estilo, con 4–5 arquetipos documentados (barra
  flotante en píldora, header editorial centrado, barra lateral, header
  transparente sobre hero, footer grande con navegación). Se conserva la lógica
  (`user`, logout POST, CSRF) en un partial aparte para que reescribir la parte
  visual no la rompa.
- **Ejemplos neutralizados.** `home.html` y el ejemplo de `kiro-feature` dejan de
  ser cards en rejilla; comentario explícito "esto es andamio, no diseño" y el
  listado de ejemplo usa `divide-y`, señalando a `DESIGN.md` para la forma real.
- **Tema de Basecoat por estilo.** Tabla estilo → tema en la skill
  (brutalista → `sera`, suave → `luma`/`maia`…), y `/kiro-init` lo cambia.

### Fase 2 — Paleta completa y tipografía con un comando

- **`make brand`** (extiende `make brand-colors`): a partir de
  `primary`, `neutral=warm|cool|pure|tinted`, `secondary` opcional y
  `surface=light|dark|cream|…`, deriva en OKLCH **todos** los tokens
  (`--background`, `--foreground`, `--card`, `--muted`, `--border`,
  `--secondary`, `--accent`…) claro y oscuro, con chequeo WCAG de cada par
  texto/fondo. Reutiliza `rgb_to_oklch`, `oklch_to_rgb`, `contrast_ratio`,
  `render_brand_block`, `apply_brand_block` de `app/branding.py`.
- **`make font name="Space Grotesk" weights="400,700" role=display`**: descarga
  los `.woff2` de Fontsource a `app/static/fonts/`, escribe `@font-face` y
  `--font-display`/`--font-sans` en un bloque delimitado de `input.css`
  (mismo patrón idempotente que el bloque de marca). Valida que el archivo sea
  woff2 por la firma de bytes.
- **Catálogo de parejas tipográficas** (`references/type-pairings.md`): ~25
  combinaciones agrupadas por estilo (incluidas serif editoriales, condensadas,
  mono, display raras), para que cada proyecto elija una distinta.
- Relajar en la skill: serif permitida en estilos editorial/expresivo, hasta 3
  pesos en la display.

### Fase 3 — Motor de variación (lo que más acerca a "experimental y único")

- **`references/archetypes.md`**: catálogo generativo traído y adaptado del
  original: arquetipos de hero (split, tipografía gigante cortada, bento
  asimétrico, editorial a dos columnas, marquee, sticky-stack, horizontal-pan),
  de sección, de textura (grano, rejilla visible, malla de gradiente, duotono,
  ilustración SVG hecha a mano, formas recortadas, stickers rotados) y de
  navegación. Cada uno con su caída a móvil.
- **"Firma visual" en `DESIGN.md`**: nueva sección obligatoria con 2–3 gestos
  distintivos que el proyecto se compromete a repetir ("titulares en serif
  condensada a 12vw que se salen del borde", "rejilla de 12 columnas visible en
  hairlines", "todo en mayúsculas mono con un acento ácido"). Más los arquetipos
  elegidos de hero/sección/textura. Esto es lo que hace que dos proyectos con el
  mismo preset no se parezcan.
- **`/kiro-init` propone 3 direcciones, no una lista.** En vez de "elige
  minimalista / suave / …", genera tres direcciones contrastadas (una segura,
  una atrevida, una experimental) con paleta, fuentes, arquetipos y firma, y el
  usuario elige o mezcla.
- **Más estilos con referencia**: escribir `references/expressive.md` y añadir
  `editorial`, `neo-brutalista` (color plano, bordes negros, sombras duras),
  `retro/y2k`, `orgánico`, `oscuro-tecnológico`. Vendorizar `redesign-skill` y
  `brandkit` del upstream (con licencia en `NOTICE.md`).
- **Imágenes y visuales**: portar §4.8 adaptado: el hero necesita un visual real
  (foto aportada por el usuario en `app/static/img/`, SVG ilustrado, patrón
  generativo en CSS); nada de páginas solo-texto ni maquetas de producto hechas
  con `div`.
- **Movimiento**: ver el análisis específico más abajo.

### Fase 4 — Bucle visual (que la IA vea y corrija)

- **Página de estilo `/_design`** (solo en desarrollo, `settings` controla si se
  monta): muestra tokens, escala tipográfica, botones, formularios, una card, un
  hero de prueba, en claro y oscuro. Es donde se itera la identidad antes de
  construir features.
- **Comando `/kiro-design-review`**: arranca `make dev`, captura la página a
  375 px y 1280 px (Claude in Chrome si está disponible; si no, pide captura al
  usuario), la contrasta con `DESIGN.md` + checklist anti-slop + "¿se parece a
  la plantilla por defecto?", y corrige en hasta 2 pasadas. Basado en
  `redesign-skill`.

## Análisis: motion con JavaScript

Hoy la skill limita el movimiento a transiciones CSS y pide "preguntar antes de
vendorizar". Es la razón por la que `MOTION_INTENSITY` alto no produce nada
distinto de uno bajo. Cómo encajaría JS en Kiro:

### Qué ya está a favor
- **Sin Node no es un problema**: GSAP, Motion y Lenis publican builds UMD de un
  solo archivo. Se descargan una vez a `app/static/js/vendor/` como ya se hace
  con `htmx.min.js` y `basecoat.min.js` (ADR-0005 se cumple: vendorizado, sin CDN).
- **La CSP lo permite**: `script-src 'self'` acepta archivos propios, y animar
  vía `element.style` / Web Animations API no lo bloquea `style-src`.
- **Licencia**: GSAP y todos sus plugins (ScrollTrigger, SplitText…) son
  gratuitos también para uso comercial desde 2025.

### Opciones

| Librería | Peso aprox. (min+gzip) | Fuerte en | Encaje en Kiro |
|---|---|---|---|
| CSS nativo (`animation-timeline: view()`, `@starting-style`) | 0 | reveals, parallax ligero, entradas | Ideal hasta motion 5–6. Soporte parcial en Firefox: degradar a estático |
| Helper propio `motion.js` (IntersectionObserver + `data-*`) | ~1–2 KB | reveals escalonados, contadores, marquee | Muy bueno: lo escribimos nosotros, cero dependencias |
| **Motion** (motion.dev, vanilla) | ~5–20 KB según módulos | `animate`, `scroll`, `inView`, springs | Bueno: ligero, API simple; menos potente en timelines largos |
| **GSAP + ScrollTrigger** | ~45 KB | pin, scrub, timelines, SplitText, horizontal-pan | El más potente; lo que usan las webs tipo Awwwards |
| Lenis (smooth scroll) | ~4 KB | scroll suave | Solo como complemento de GSAP en motion 9–10 |

(Los pesos son orientativos; se miden al vendorizar.)

### Riesgos y cómo se resuelven
1. **SEO / contenido sin JS.** Si un elemento empieza con `opacity:0` en CSS y
   el JS falla, la página queda en blanco. Regla: el estado inicial oculto solo
   se aplica bajo una clase `.js-motion` que el propio script pone en `<html>`.
   Sin JS, todo visible (requisito 3 de AGENTS.md intacto).
2. **HTMX reemplaza el DOM.** Los fragmentos que llegan por `hx-get` no se
   animan solos. Solución: inicializar con `htmx.onLoad(el => …)`, que se
   dispara en la carga y en cada swap; y matar los ScrollTrigger del fragmento
   reemplazado para no filtrar memoria.
3. **Reduced motion.** `gsap.matchMedia()` / `prefers-reduced-motion` envuelve
   toda la inicialización; con reduced motion, nada se mueve.
4. **Peso en páginas que no lo necesitan.** Se carga solo en
   `layouts/landing.html` (bloque `scripts`), nunca en pantallas privadas.
5. **Que la IA escriba JS distinto en cada página.** Es el mayor riesgo de
   mantenimiento. Solución: **API declarativa por atributos**, un único
   `app/static/js/motion.js` del proyecto, y la IA solo escribe Jinja:
   ```html
   <h1 data-motion="split-reveal">…</h1>
   <ul data-motion="stagger" data-motion-delay="0.08">…</ul>
   <section data-motion="pin" data-motion-scrub>…</section>
   ```

### Recomendación por niveles de `MOTION_INTENSITY`

| Dial | Qué se usa |
|---|---|
| 1–3 | Solo transiciones CSS (hover, focus, `:active`) |
| 4–6 | CSS scroll-driven + helper `motion.js` propio (reveals, stagger, contadores) |
| 7–8 | + **Motion** vendorizado (springs, `scroll()` ligado a progreso) |
| 9–10 | + **GSAP + ScrollTrigger** (+ SplitText, Lenis opcional): pin, scrub, horizontal-pan, sticky-stack |

Se instalaría con un comando (`make motion level=gsap`) que descarga y valida
los archivos, igual que `make logo`, y un ADR que documente la excepción. Así
el dial deja de ser decorativo: cambiarlo cambia de verdad lo que la IA tiene
disponible.

## Archivos críticos (si en el futuro se implementa)

- `app/templates/base.html`, nuevos `app/templates/layouts/{app,landing}.html`
- `app/templates/partials/header.html`, `footer.html`, nuevo `partials/nav_auth.html`
- `app/templates/pages/home.html`, `.claude/skills/kiro-feature/SKILL.md`
- `app/branding.py` (paleta completa, bloque de fuentes), `scripts/brand.py`, `Makefile`
- `.claude/skills/kiro-design/SKILL.md` + `references/` (archetypes, type-pairings, expressive, editorial, neo-brutalist…, redesign, brandkit)
- `DESIGN.md` (secciones Firma visual, Arquetipos, Tema Basecoat, Superficie)
- `.claude/commands/kiro-init.md`, nuevo `.claude/commands/kiro-design-review.md`
- `docs/decisions/0014-…` (variación de diseño, layouts, fuentes y motion vendorizados)
- `tests/test_branding.py` (paleta completa, contraste de cada par, bloque de fuentes, validación woff2)

## Cómo se verificaría (cuando se implemente)

1. `make check` en verde (mypy strict sobre `app/branding.py`, tests nuevos).
2. `make brand primary="#C2410C" neutral=warm surface=cream` y
   `make font name="Fraunces" role=display` → `make css` → `/_design` muestra
   fondo crema, texto cálido y la serif en titulares.
3. Prueba de convergencia: aplicar 3 `DESIGN.md` distintos (minimalista,
   neo-brutalista, editorial) sobre el mismo proyecto, generar la portada con
   cada uno y comparar capturas a 1280 px: deben diferir en layout, tipografía y
   superficie, no solo en el color del botón.
4. Comprobar que login, registro y notas siguen funcionando con
   `layouts/app.html` (tests existentes de auth y notes).
