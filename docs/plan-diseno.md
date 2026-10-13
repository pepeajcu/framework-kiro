# Cara a cara: los tres análisis y la ruta definitiva

> Consolidación de `analisis-diseno.md`, `analisis-glm-5-3.md` y
> `analisis-minimaxm3.md` · 2026-10-13. Estado del repo verificado antes de
> escribir esto: `brand_tokens` solo deriva `--primary`,
> `--primary-foreground` y `--ring` (`app/branding.py:227`); `base.html:85`
> fija `max-w-5xl` para todo; `/kiro-init` **ya existe** en
> `.claude/commands/`; solo hay 3 referencias vendorizadas; no existe
> `make font`, ni `app/templates/layouts/`, ni `app/static/fonts/`.

> ## ⚠️ Punto de retorno (leer antes de implementar)
>
> **Este commit es el checkpoint antes de ejecutar el plan de diseño.** Solo
> contiene los 4 documentos de análisis/plan: **cero código del framework fue
> tocado**. El framework funciona exactamente como en v1.1.0.
>
> Si el plan no funciona o quieres volver atrás:
>
> ```bash
> git log --oneline                  # localiza este commit (docs: checkpoint)
> git reset --hard <este-commit>     # descarta todo lo hecho después
> ```
>
> Qué contiene este punto, en una línea: framework estable con identidad de
> marca por tokens (`make brand-colors`, `make logo`, `/kiro-init`) pero con
> el problema de convergencia diagnosticado en los análisis: todas las apps
> heredan el mismo esqueleto gris y solo cambia el color del botón. Las fases
> 1–4 de este documento son la forma de arreglarlo; hasta entonces, nada
> está implementado.

## 1. El enfrentamiento

| | **diseno** | **glm-5-3** | **minimaxm3** |
|---|---|---|---|
| Diagnóstico | 8 causas, las más profundas: solo 3 tokens de ~20 cambian; esqueleto HTML fijo; skill = solo prohibiciones; se perdió la parte generativa de taste-skill; la IA nunca ve lo que diseña | 7 causas correctas pero menos profundas (no ve el contenedor fijo ni el problema de tokens) | 5-6 causas válidas pero **una desactualizada**: dice que `/kiro-init` es un "comando fantasma" — ya existe |
| Solución | 4 fases ordenadas por impacto/esfuerzo, con `make brand` de paleta completa, `make font`, firma visual, motor de arquetipos, bucle visual y análisis de motion con riesgos reales | 8 propuestas en tabla; aporta defaults por preset, `/kiro-redesign` para rescatar apps existentes y el flujo "referencia visual primero" | Agrupadas por esfuerzo; aporta la mecánica de plantillas más concreta (variantes de header/hero, macros de sección) pero también las propuestas más arriesgadas |
| Motion | El único que analiza riesgos: página en blanco sin JS, HTMX que reemplaza el DOM, reduced motion, API declarativa por `data-*` | Conservador: recetario CSS/vanilla | `kiro-motion.js` con data-attributes — misma idea que diseno, menos desarrollada |
| Verificación | El único con plan de verificación, incluida prueba de convergencia | No incluye | No incluye |

**Los tres convergen en el mismo diagnóstico nuclear**, con distinta
profundidad: la identidad solo cambia pintura (tokens) y nunca arquitectura
(estructura de página); los presets expresivos no tienen receta; la tipografía
es un paso manual que la IA salta; el motion por encima del dial 4 no existe
porque hay que pedir permiso; y `home.html` es el patrón propagador que la IA
imita.

## 2. Veredicto

**La ruta base es la de `analisis-diseno.md`.** Es el diagnóstico más profundo
y el único pipeline completo, y es el único que ataca lo que los otros dos ni
ven: que con el fondo, texto, card, muted y border siempre en el gris neutro de
Basecoat, **cualquier cambio de estructura se lee igual de gris**. Sus fases
además están ordenadas para que cada una entregue valor sola.

De los otros dos se absorbe lo mejor:

- **De glm:** defaults por preset (tema, radio, fuente sugerida se aplican
  solos al elegir estilo — variedad incluso con relleno perezoso) y
  `/kiro-redesign` para rescatar las 7 apps ya construidas.
- **De minimax:** las 4 variantes concretas de header (sticky-blur,
  floating-pill, industrial-rule, terminal-bar) como los arquetipos de
  navegación de la fase 1, y las macros de patrones de sección
  (`eyebrow_heading`, `bento_grid`) como parte del catálogo de arquetipos.

**Se descarta:**

- **minimax A** (crear `/kiro-init`): ya existe. Análisis hecho sobre una
  foto vieja del repo.
- **minimax D** (default `vega` → `nova`): cosmético y contradice el flujo —
  el default debe empujar a correr `/kiro-init`, no a verse "más agency" sin
  configurar nada.
- **minimax G** (starters completos de home por preset): es una tienda de
  plantillas, no diseño generativo. Cinco homes precocinados que mantener y que
  la IA vuelve a imitar — el problema original con otro disfraz. Se reemplaza
  por arquetipos + home neutralizada.
- **minimax J** (overrides de diseño por página vía front-matter en
  `render()`): la única propuesta que toca el core del framework, para valor
  marginal. Un proyecto elige una identidad; si necesita dos, son dos
  secciones de la misma, no dos sistemas de tokens.
- **glm 3** (presets `neon-tech`, `retro-terminal` separados): se pliegan a la
  lista de nuevos estilos de diseno (`retro/y2k`, `oscuro-tecnológico`).

## 3. El plan

### Fase 0 — Registrar la decisión

ADR-0014: variación de diseño, layouts, `make brand` completo, fuentes
vendorizadas y motion vendorizado con niveles por dial. Es una excepción
documentada a "no vendorices sin preguntar", así que va por escrito antes de
tocar código.

### Fase 1 — Quitar los homogeneizadores (alto impacto, bajo esfuerzo)

1. **Layouts.** `base.html` deja el contenedor en `{% block main %}`; se crean
   `layouts/app.html` (el `max-w-5xl` actual, pantallas privadas) y
   `layouts/landing.html` (a sangre, secciones propias, con bloque `scripts`).
   Las páginas existentes extienden `app.html`; nada se rompe.
2. **Header y footer como identidad.** La lógica (`user`, logout POST, CSRF)
   se aísla en `partials/nav_auth.html`; `kiro-design` exige reescribir la parte
   visual al aplicar estilo, con los 4 arquetipos de minimax documentados:
   sticky-blur, floating-pill, industrial-rule, terminal-bar.
3. **Ejemplos neutralizados.** `home.html` y el ejemplo de `kiro-feature`
   dejan de ser "badge + h1 + grid de cards": comentario explícito de andamio,
   listado con `divide-y`, y señalar a `DESIGN.md` para la forma real.
4. **Tema Basecoat por estilo.** Tabla estilo → tema (brutalista → `sera`,
   suave → `luma`/`maia`…) en la skill; `/kiro-init` lo aplica. (Absorbido de
   glm #8 / minimax C.)

### Fase 2 — Paleta completa y tipografía con un comando

1. **`make brand`** (extiende `brand-colors`): desde `primary`,
   `neutral=warm|cool|pure|tinted`, `secondary` opcional y
   `surface=light|dark|cream|…`, deriva en OKLCH **todos** los tokens
   (`--background`, `--foreground`, `--card`, `--muted`, `--border`,
   `--secondary`, `--accent`…) claro y oscuro, con chequeo WCAG de cada par
   texto/fondo. Reutiliza `rgb_to_oklch`, `oklch_to_rgb`,
   `contrast_ratio`, `render_brand_block`, `apply_brand_block`.
2. **`make font name="Fraunces" weights="400,700" role=display`**: descarga
   `.woff2` de Fontsource a `app/static/fonts/` (validación por firma de
   bytes), escribe `@font-face` y `--font-display`/`--font-sans` en un bloque
   delimitado e idempotente de `input.css`.
3. **`references/type-pairings.md`**: ~25 parejas por estilo (incluidas serif
   editoriales, condensadas, mono, display). Relajar la skill: serif permitida
   en editorial/expresivo, hasta 3 pesos en la display.
4. **Tests** en `tests/test_branding.py`: cada par texto/fondo pasa WCAG,
   bloque de fuentes idempotente, woff2 validado.

### Fase 3 — Motor de variación (lo que hace únicos a dos proyectos gemelos)

1. **`references/archetypes.md`**: hero (split, tipografía gigante, bento
   asimétrico, editorial, marquee, sticky-stack, horizontal-pan), sección,
   textura (grano, rejilla, gradiente, duotono) y navegación, con caída a
   móvil. Más macros de sección de minimax (`eyebrow_heading`, `bento_grid`).
2. **Firma visual obligatoria en `DESIGN.md`**: 2–3 gestos que el proyecto se
   compromete a repetir + arquetipos elegidos. Dos proyectos con el mismo
   preset ya no se parecen.
3. **`/kiro-init` propone 3 direcciones** (segura, atrevida, experimental) con
   paleta, fuentes, arquetipos y firma — no una lista sesgada a lo sobrio.
4. **Referencias que faltan** (los tres análisis lo piden): `expresivo.md`,
   `institucional.md`, `panel-de-datos.md`, y luego `editorial`,
   `neo-brutalista`, `retro/y2k`, `orgánico`, `oscuro-tecnológico`.
5. **Imágenes**: portar §4.8 de taste-skill — el hero necesita un visual real;
   nada de páginas solo-texto ni maquetas con `div`.
6. **Motion con niveles reales por dial:**

   | Dial | Qué se usa |
   |---|---|
   | 1–3 | Solo transiciones CSS |
   | 4–6 | CSS scroll-driven + `motion.js` propio (~1–2 KB, IntersectionObserver) |
   | 7–8 | + Motion (motion.dev) vendorizado |
   | 9–10 | + GSAP + ScrollTrigger (+ SplitText, Lenis opcional) |

   Reglas de seguridad (de diseno, los otros dos no las tenían): estado oculto
   solo bajo clase `.js-motion` que pone el propio script (sin JS todo visible
   — regla 3 de AGENTS intacta), inicialización vía `htmx.onLoad` y limpieza de
   triggers del fragmento saliente, `matchMedia` reduced-motion, carga solo en
   `layouts/landing.html`. `make motion level=…` instala y valida; la IA solo
   escribe `data-motion="split-reveal"` — jamás JS por página.
7. **`/kiro-redesign`** (de glm): audita una app ya construida contra su
   `DESIGN.md` y empuja varianza — rescata las 7 existentes.

### Fase 4 — Bucle visual (que la IA vea lo que diseña)

1. **`/_design`** (solo en desarrollo, flag en `settings`): tokens, escala
   tipográfica, botones, form, card, hero de prueba, claro y oscuro. Donde se
   itera la identidad antes de construir features.
2. **`/kiro-design-review`**: arranca `make dev`, captura a 375 px y 1280 px
   (Claude in Chrome si está; si no, pide captura), contrasta con `DESIGN.md` +
   anti-slop + "¿se parece al default?", corrige hasta en 2 pasadas.
3. **`make preview-style name="…"`** (de minimax K): showcase del estilo antes
   de elegirlo. Se monta sobre `/_design`, no es pieza aparte.

## 4. Por qué este orden

1. Sin Fase 1 no hay dónde desplegar ninguna identidad: todo lo demás seguiría
   cayendo dentro del mismo `max-w-5xl` con el mismo header.
2. Sin Fase 2 cualquier estructura nueva se lee igual de gris: el fondo y el
   texto son el 80 % de los píxeles de una página.
3. La Fase 3 es lo que separa proyectos entre sí; la 4 lo que separa el
   primer borrador del final. Cada fase entrega valor sola y las 1–2 son
   baratas.

## 5. Verificación final

1. `make check` en verde (mypy strict sobre `branding.py`, tests nuevos).
2. `make brand primary="#C2410C" neutral=warm surface=cream` +
   `make font name="Fraunces" role=display` → `make css` → `/_design` muestra
   fondo crema, texto cálido, serif en titulares.
3. **Prueba de convergencia**: aplicar 3 `DESIGN.md` distintos (minimalista,
   neo-brutalista, editorial) al mismo proyecto y comparar capturas a 1280 px:
   deben diferir en layout, tipografía y superficie, no solo en el color del
   botón.
4. Login, registro y notas siguen pasando con `layouts/app.html` (tests
   existentes de auth y notes).
