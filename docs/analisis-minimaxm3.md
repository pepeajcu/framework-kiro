# Análisis del framework y propuestas para diversificar el diseño

## Por qué todas tus apps se ven iguales (causas raíz)

La buena noticia: el framework **ya tiene los mecanismos correctos** (`DESIGN.md` con diales, `make brand-colors`, los presets de estilo, las 8 variantes de tema de Basecoat, las references de taste-skill, las anti-slop rules). El problema no es que falten piezas — es que la **adopción está rota por defecto**. Hay 5 motivos concretos:

### 1. `DESIGN.md` arranca con TODOs y la IA no lo nota

`DESIGN.md:13` dice literalmente `Estilo: TODO`, y lo mismo en cada dial, color y radio. La regla de oro de la skill `kiro-design/SKILL.md:21-24` es:

> Si `DESIGN.md` tiene `TODO`, **para y pide al usuario que corra `/kiro-init`**.

Si el usuario (o la IA) ignora eso, la IA entra a construir con cero brief de marca → cae al mínimo Basecoat por defecto.

### 2. `/kiro-init` está referenciado pero no existe como comando

`DESIGN.md:4` y la propia `kiro-design/SKILL.md` lo citan varias veces, pero no encontré ningún `app/templates/pages/init.html`, ni un router `/init`, ni un skill llamado `kiro-init` que lo automatice. Es un comando fantasma. Mientras no exista, todo queda en disciplina manual.

### 3. El default es exactamente la cara "shadcn genérica"

- Tema importado: `vega` (`app/static/css/input.css:12`) — el más neutro de los 8 disponibles.
- `--radius: 0.625rem` (`app/static/css/vendor/basecoat/base/base.css:4`) — radio Basecoat genérico.
- `--font-sans: "Geist Sans"` y `--font-mono: "Geist Mono"` (`base.css:87-88`) — los defaults.
- Si nadie corre `make brand-colors`, `make logo` y `make font`, todo se queda en ese gris con esquinas suaves y Geist Sans. **Eso es lo que se repite en tus 7 proyectos**.

### 4. La página de ejemplo enseña el patrón repetido

`app/templates/pages/home.html` es la "página viva" que la IA lee como referencia (lo dice `home.html:2-11`). Y lo que enseña es:

- `<section class="space-y-3">` con un `badge` + `h1` + `text-muted-foreground`
- Una grilla de `card` Basecoat (`home.html:33-59`)
- Botón `btn data-variant="primary"` con HTMX

Esto es el **patrón propagador**. La IA lo imita en cada nueva página porque es lo único que vio renderizado bonito en el framework.

### 5. Tres de seis presets de estilo **no tienen referencia vendorizada**

`kiro-design/SKILL.md:43-50` define 6 presets (`minimalista`, `suave-premium`, `brutalista`, `institucional`, `expresivo`, `panel-de-datos`). Las **únicas 3 referencias** que existen en `kiro-design/references/` son `minimalist.md`, `soft.md` y `brutalist.md`. Para los otros 3 la IA tiene solo los diales y las reglas generales — sin guía visual concreta, vuelve a caer en el Basecoat genérico.

### 6. Los partials comunes son una sola plantilla fija

`app/templates/partials/header.html:3` es la misma cabecera pegada al borde con `backdrop-blur` para todos los estilos. No existe una variante "floating pill" (suave-premium), ni una "topbar industrial con reglas visibles" (brutalista), ni una "terminal monospace" (panel-de-datos). Toda app que herede `base.html` arranca igual.

---

## Propuestas concretas, ordenadas por impacto

Las agrupo en **rápidas** (sin tocar arquitectura), **medias** (un par de archivos bien elegidos) y **grandes** (estructurales).

### 🟢 Rápidas — máximo ROI

**A. Crear `kiro-init` como slash command real**

Es la pieza más crítica que falta. Convierte `DESIGN.md` de TODO en un brief rellenado en 3 minutos.

- Nueva skill en `.claude/skills/kiro-init/SKILL.md` que conduce una entrevista: estilo → diales (V/M/D) → paleta → radio → tipografía → logo.
- Cada respuesta ejecuta el comando correspondiente (`make brand-colors`, `make font`, `make logo`).
- Cierra con un `make css` y un checklist de lo aplicado.

Resultado: el "ya parece Basecoat" desaparece desde el primer paso.

**B. Rellenar las 3 referencias que faltan**

Sólo texto, no código. Crear `kiro-design/references/institucional.md`, `expresivo.md`, `panel-de-datos.md` siguiendo el mismo formato que las 3 existentes (archetipos, tipografía, color, layout, motion, checklist). Esto cierra la grieta principal por la que la IA "inventa" un estilo para los presets sin documentación.

**C. Comandos `make` pre-configurados de tipo preset**

Hoy `make brand-colors` solo toma `--primary` y `--radius`. Añadir presets que aplican **todo el lote**:

```
make preset name="editorial"          # tema nova + radius 0.5rem + Geist+Instrument Serif + dials 5/3/2
make preset name="agencia"            # tema maia + radius 1.5rem + Satoshi+PP Editorial + dials 7/6/3
make preset name="terminal"           # tema lyra + radius 0rem + JetBrains Mono + dials 3/2/8
make preset name="industrial"         # tema vega + radius 0rem + Inter Black+EB Garamond + dials 9/4/6
```

Cada uno descarga `.woff2` locales, escribe el bloque `kiro:brand` en `input.css`, cambia el import del tema y corre `make css`. **Una línea, identidad completamente diferente.**

**D. Cambiar el tema por defecto de `vega` a `nova`**

Costo: una línea en `app/static/css/input.css:12`. `nova` ya tiene esquinas más redondeadas (`rounded-lg`), sombras más suaves y proporciones que se sienten más "agency". Solo con esto la primera impresión de un proyecto recién clonado deja de parecer shadcn puro.

---

### 🟡 Medias — cambian la primera impresión de cualquier app

**E. Variantes de `partials/header.html` por estilo**

Crear `app/templates/partials/headers/` con 4 versiones:

- `sticky-blur.html` — el actual (default)
- `floating-pill.html` — flotante, `rounded-full`, `mt-6 mx-auto`, como pide el preset `suave-premium` (`soft.md:57`)
- `industrial-rule.html` — borde inferior grueso de 2px, sin blur, con marcas técnicas (`REF / 01`), para `brutalist`
- `terminal-bar.html` — monospace, `bg-foreground text-background`, ancho completo, con `[ SYS ]` y timestamp

`base.html` recibe un bloque `{% block header_partial %}` que cada `pages/<x>.html` puede sobreescribir. O `make preset` elige cuál se incluye automáticamente.

**F. Variantes de hero por estilo**

El `pages/home.html` actual tiene un solo patrón (badge + h1 + p + grid). Crear `app/templates/components/heroes/`:

- `centered-doc.html` — el actual, para `minimalista`
- `editorial-split.html` — tipografía display a la izquierda, contenido interactivo a la derecha (`soft.md:34-36`)
- `asymmetric-bento.html` — grilla CSS con `col-span-8` y `col-span-4` (`soft.md:30-32`)
- `terminal-telemetry.html` — data densa monospace con ASCII brackets (`brutalist.md:75-80`)
- `manifesto-fullbleed.html` — tipografía `clamp(4rem, 10vw, 15rem)` a sangre completa (`brutalist.md:30-32`)

**G. Page starters por preset**

Crear `app/templates/pages/_starts/{minimalista,suave-premium,brutalista,expresivo,panel-de-datos}/home.html`. Cuando un proyecto selecciona preset, en lugar del home genérico de Basecoat obtiene una página de inicio ya estilizada para ese lenguaje. **Esta es la palanca más fuerte contra el "todo se ve igual"**, porque es lo primero que la IA ve y, por tanto, lo primero que imita.

**H. Macros de patrones de sección**

`app/templates/components/sections/` con macros para los patrones recurrentes que las references mencionan pero que la IA reescribe mal cada vez:

- `bento_grid(items, cols=...)`
- `eyebrow_heading(label, title, subtitle)` — con la regla de "máx uno por cada 3 secciones"
- `z_cascade(items)` — para el layout Z-Axis de `soft.md:32-36`
- `data_table_telemetry(rows)` — para `panel-de-datos`

---

### 🟠 Grandes — estructurales, transforman el framework

**I. Motion presets como CSS reutilizable, sin librería**

Hoy `kiro-design/SKILL.md:152-156` dice "a `MOTION_INTENSITY <= 4` con CSS basta; arriba de eso, pregunta antes de vendorizar". Eso significa que la IA nunca aplica motion cinematográfico. Solución: vender un mini-bundle de animaciones CSS/JS en `app/static/js/kiro-motion.js` (~3 KB) que la IA pueda importar cuando `MOTION_INTENSITY > 5`:

- `data-kiro-animate="fade-up"` → `IntersectionObserver` + clase que resuelve `translate-y-4 opacity-0` a `translate-y-0 opacity-100`.
- `data-kiro-animate="stagger"` → cascade delay con `--index`.
- `data-kiro-stagger="80"` → delay entre hijos.

`base.html` lo carga solo si el dial lo pide. Cero JS frameworks, respeta `prefers-reduced-motion` (ya está en la regla), y desbloquea los presets `suave-premium` y `expresivo` que hoy no pueden mostrarse como fueron diseñados.

**J. Page-level "design overrides"**

Permitir que `pages/<x>.html` declare en el front-matter algo como:

```jinja
{% design style="expresivo" dial_v=9 dial_m=8 dial_d=3 %}
```

Y un hook en `render()` (ya existe en `app/templating.py`) que, cuando detecta esto, aplica overrides locales encima de los tokens globales. Esto permite que **dentro de un mismo proyecto** convivan:

- Landing pública agresiva (`expresivo`)
- Backoffice denso (`panel-de-datos`)
- Página de pricing sobria (`institucional`)

Sin tener que crear proyectos separados para cada uno.

**K. Catálogo visual de "estilo en acción"**

Un comando `make preview-style name="brutalista"` que arranca un showcase estático en `localhost:<port>/_style/<name>` con:

- Los 4 hero variants
- Las 3 secciones típicas
- Las 2 paletas (clara/oscura)
- La tipografía cargada
- Una página 404 y un formulario de ejemplo

Para que, antes de elegir preset, **veas** lo que va a salir. Hoy la decisión se toma a ciegas leyendo un `.md`.

---

## Mi recomendación si tuviera que elegir tres

Si quieres moverte esta semana y ver un cambio radical entre proyectos sin tocar la arquitectura:

1. **A** (crear `/kiro-init` como skill real) — cierra la puerta de TODOs.
2. **G** + **E** (page starters y headers por preset) — ataca directamente las dos cosas que la IA mira primero cuando arranca.
3. **C** (`make preset name=...`) — una línea y un proyecto entero se transforma.

Esos tres resuelven ~80% del problema. El resto (motion, overrides, catálogo) son multiplicadores para cuando ya tengas los presets adoptados.

¿Quieres que arranquemos con alguno? El más impactante y aislado es el **(A)** — puedo escribir la skill `kiro-init` completa en una sesión.
