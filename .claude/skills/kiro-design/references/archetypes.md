# Archetypes: the catalogue of shapes

A style says how a project *feels*. An archetype says how a page is *built*. This
file is a menu of structures, each with working markup, its mobile fallback and
the dials it suits. Pick them in `/kiro-init` and record the choice in
`DESIGN.md` under **Arquetipos**; the project's **Firma visual** (its own
gestures) goes on top and is never taken from here.

**How to use it.** These are recipes, not templates to paste. Take the structure,
write the project's real content in it, and change what the project's identity
asks you to change. Two projects that choose the same hero must still look
different, because the type, colour, radius and signature differ.

**Rules for every snippet below**

- A section's vertical padding is `section-y` (and a grid's gap can be `gap-rhythm`): they
  come from `[structure] density`, so the same archetype is airy in a gallery and tight in a
  cockpit. Do not write `py-16` for a section.

- Tokens only (`bg-primary`, `text-muted-foreground`, `border-border`); never a hex.
- Every multi-column layout names its `< 768px` fallback in the same element.
- The hero fits the first viewport (`min-h-[100dvh]` at most, never `h-screen`).
- Content is in the HTML the server sends. Motion is `data-motion` attributes
  (level in `design.toml`); without JS or with reduced motion the page is static
  and complete.
- A visual is a real asset: an SVG, or a photo under `app/static/img/`. Not a
  `div` pretending to be a screenshot, and not an external URL (the CSP is
  `img-src 'self' data:`).
- Pages extend `layouts/landing.html`; each `<section>` puts its own container
  *inside* itself (`<div class="mx-auto max-w-6xl px-4">`), so header, content
  and footer share one edge.

---

## 1. Heroes

### 1.1 `split`: text and visual, off-balance

When: most products with something to show. `DESIGN_VARIANCE` 4+.
Never 50/50: give the text 7 columns and the visual 5, or the reverse.

```html
<section class="section-y">
  <div class="mx-auto grid max-w-6xl items-center gap-10 px-4 lg:grid-cols-12">
    <div class="lg:col-span-7">
      <h1 class="text-5xl leading-[1.02] tracking-tight text-balance sm:text-7xl" data-motion="split-reveal">
        Un titular de dos líneas como máximo
      </h1>
      <p class="text-muted-foreground mt-6 max-w-md text-lg text-pretty" data-motion="reveal" data-motion-delay="0.2">
        Una frase de veinte palabras que dice qué es y para quién.
      </p>
      <div class="mt-8 flex flex-wrap gap-3" data-motion="reveal" data-motion-delay="0.3">
        <a class="btn" data-variant="primary" data-size="lg" href="/register">Acción principal</a>
        <a class="btn" data-variant="ghost" data-size="lg" href="#como">Cómo funciona</a>
      </div>
    </div>
    <div class="lg:col-span-5">
      <!-- el visual real: <img src="{{ asset('img/hero.webp') }}" alt="..." width="..." height="..."> -->
      <div class="bg-muted aspect-[4/5] rounded-xl"></div>
    </div>
  </div>
</section>
```

Mobile: the grid is one column, so the visual drops under the text. Give it a
shorter ratio there (`aspect-[16/10] lg:aspect-[4/5]`) so it does not push the
call to action below the fold.

### 1.2 `type-giant`: the headline is the visual

When: brands with a strong name or one idea; no usable imagery. `DESIGN_VARIANCE` 7+.
Needs a display face with presence (see `type-pairings.md`).

```html
<section class="flex min-h-[100dvh] flex-col justify-end overflow-hidden pb-10">
  <div class="mx-auto w-full max-w-[110rem] px-4">
    <h1 class="text-[clamp(3.5rem,13vw,13rem)] leading-[0.85] font-semibold tracking-tighter uppercase" data-motion="split-reveal">
      Nombre<br>del proyecto
    </h1>
    <div class="border-foreground mt-8 flex flex-wrap items-end justify-between gap-6 border-t pt-4">
      <p class="max-w-sm text-sm text-pretty">Una línea que lo explica.</p>
      <a class="btn" data-variant="primary" data-size="lg" href="/register">Entrar</a>
    </div>
  </div>
</section>
```

`<br>` inside a `split-reveal` makes the element "have tags" and the script
leaves it static; for a staggered reveal write one `<span class="block" data-motion="reveal">`
per line instead. Mobile: `clamp()` keeps the type from overflowing; check at 375 px.

### 1.3 `bento`: an asymmetric grid of different-sized tiles

When: a product with several equal-weight facts. `DESIGN_DENSITY` 4+. Tiles must
differ in size *and* in content type (a number, a quote, a visual, a list).

```html
<section class="section-y">
  <div class="mx-auto max-w-6xl px-4">
    <h1 class="max-w-3xl text-4xl tracking-tight text-balance sm:text-6xl">Titular</h1>
    <div class="mt-10 grid auto-rows-[10rem] gap-3 sm:grid-cols-2 lg:grid-cols-6" data-motion="stagger" data-motion-delay="0.07">
      <div class="bg-primary text-primary-foreground rounded-xl p-6 sm:col-span-2 lg:col-span-3 lg:row-span-2">Tile grande: la idea</div>
      <div class="bg-muted rounded-xl p-6 lg:col-span-3">Tile ancho</div>
      <div class="bg-card border-border rounded-xl border p-6 lg:col-span-1"><span class="text-5xl">24</span></div>
      <div class="bg-card border-border rounded-xl border p-6 lg:col-span-2">Tile medio</div>
    </div>
  </div>
</section>
```

Mobile: one column at `auto-rows`; drop the `row-span` (it only applies at `lg:`).
`stagger` makes the tiles enter in sequence.

### 1.4 `editorial`: a narrow column, a kicker and a rule

When: content-first sites, publications, long-form. `DESIGN_VARIANCE` 3-6.
Serif display, generous measure, hairline rules.

```html
<header class="section-y">
  <div class="mx-auto max-w-3xl px-4">
    <p class="text-muted-foreground font-mono text-xs tracking-widest uppercase">Número 04 · Octubre</p>
    <h1 class="mt-4 text-5xl leading-[1.05] tracking-tight text-balance sm:text-7xl">Un titular que se lee como una portada</h1>
    <p class="text-muted-foreground mt-6 text-xl text-pretty">Una entradilla de dos frases que sostiene el titular.</p>
    <div class="border-border mt-8 flex items-center justify-between border-y py-3 text-sm">
      <span>Por la redacción</span><span class="text-muted-foreground">8 min</span>
    </div>
  </div>
</header>
```

Mobile: nothing to do, it is already a column. Keep `max-w-3xl` (about 65
characters of body) and let the headline break at its natural points.

### 1.5 `marquee`: a band that never stops

When: a sector, a list of tools or clients (real ones from `PROJECT.md`, never
invented), a long tagline. Level 4+ for `data-motion="marquee"`.

```html
<section class="border-border border-y py-5">
  <div class="text-4xl font-semibold tracking-tight whitespace-nowrap" data-motion="marquee" data-motion-speed="30">
    <span>Primera cosa</span><span class="text-primary">/</span>
    <span>Segunda cosa</span><span class="text-primary">/</span>
    <span>Tercera cosa</span><span class="text-primary">/</span>
  </div>
</section>
```

Without JS it is a normal row (give the container `flex flex-wrap gap-x-6` to
let it wrap). It pauses on hover and stops entirely under reduced motion.

### 1.6 `sticky-stack`: panels that pile up as you scroll

When: a process in three or four steps. Pure CSS: it needs no motion level.

```html
<section class="section-y">
  <div class="mx-auto max-w-4xl px-4">
    <div class="bg-card border-border sticky top-24 mb-4 rounded-xl border p-8">
      <p class="text-muted-foreground font-mono text-sm">01</p><h2 class="mt-2 text-3xl">Primer paso</h2>
    </div>
    <div class="bg-card border-border sticky top-32 mb-4 rounded-xl border p-8">
      <p class="text-muted-foreground font-mono text-sm">02</p><h2 class="mt-2 text-3xl">Segundo paso</h2>
    </div>
    <div class="bg-primary text-primary-foreground sticky top-40 rounded-xl p-8">
      <p class="font-mono text-sm opacity-80">03</p><h2 class="mt-2 text-3xl">Tercer paso</h2>
    </div>
  </div>
</section>
```

Each panel's `top-*` grows by one step, so the previous one peeks out. Mobile:
works as is; reduce the offsets (`top-20`, `top-24`...) if the header is tall.

### 1.7 `horizontal-pan`: a gallery that scrolls sideways

When: a portfolio, a timeline, a catalogue of 4-8 items. Level 9+ pins it and
pans on scroll; below that, or on a phone, it is a normal swipeable row.

```html
<section class="overflow-x-auto py-12 md:py-0" data-motion="horizontal">
  <div class="flex h-full w-max snap-x items-center gap-6 px-4 md:min-h-[100dvh] md:px-12">
    <article class="bg-card border-border w-[80vw] shrink-0 snap-center rounded-xl border p-8 md:w-[40vw]">Uno</article>
    <article class="bg-card border-border w-[80vw] shrink-0 snap-center rounded-xl border p-8 md:w-[40vw]">Dos</article>
    <article class="bg-card border-border w-[80vw] shrink-0 snap-center rounded-xl border p-8 md:w-[40vw]">Tres</article>
  </div>
</section>
```

The section's first child is the track. Pinning only runs from 768 px up; on a
phone the row scrolls with a finger. Without JS it is the same swipeable row.

---

## 2. Sections

### 2.1 `statement`: one sentence, very large

A breather between dense sections. At most one per page.

```html
<section class="py-24 sm:py-40">
  <p class="mx-auto max-w-5xl px-4 text-3xl leading-tight tracking-tight text-balance sm:text-6xl" data-motion="scrub">
    Una sola frase con todo el peso del proyecto, escrita en grande.
  </p>
</section>
```

`scrub` (level 9) lights the words with the scroll; `reveal` is the lower-level
choice.

### 2.2 `numbered`: a list as a table of contents

The replacement for "three cards in a row". Rules, not boxes.

```html
<section class="section-y">
  <div class="mx-auto max-w-6xl px-4">
    <ol class="divide-border border-border divide-y border-y" data-motion="stagger">
      <li class="grid gap-2 py-6 sm:grid-cols-[6rem_1fr_1.5fr] sm:gap-8">
        <span class="text-muted-foreground font-mono text-sm">01</span>
        <h3 class="text-2xl tracking-tight">Primer punto</h3>
        <p class="text-muted-foreground text-pretty">Qué es, en una o dos frases.</p>
      </li>
      <li class="grid gap-2 py-6 sm:grid-cols-[6rem_1fr_1.5fr] sm:gap-8">
        <span class="text-muted-foreground font-mono text-sm">02</span>
        <h3 class="text-2xl tracking-tight">Segundo punto</h3>
        <p class="text-muted-foreground text-pretty">Qué es, en una o dos frases.</p>
      </li>
    </ol>
  </div>
</section>
```

Mobile: the grid collapses to a stack (`sm:` only adds columns).

### 2.3 `spec-sheet`: facts as a definition list

For products with real specifications, rates, hours, ingredients.

```html
<section class="section-y">
  <div class="mx-auto max-w-4xl px-4">
    <dl class="divide-border border-border divide-y border-y">
      <div class="grid gap-1 py-4 sm:grid-cols-[14rem_1fr]">
        <dt class="text-muted-foreground text-sm">Capacidad</dt><dd class="font-mono">12 personas</dd>
      </div>
      <div class="grid gap-1 py-4 sm:grid-cols-[14rem_1fr]">
        <dt class="text-muted-foreground text-sm">Horario</dt><dd class="font-mono">09:00 a 18:00</dd>
      </div>
    </dl>
  </div>
</section>
```

### 2.4 `dark-band`: a dark section inside a light page

A dark call to action or footer. `class="dark"` re-maps every token under it
(the compiler writes the mapping), so the same utilities work inside.

```html
<section class="dark bg-background text-foreground py-20">
  <div class="mx-auto flex max-w-6xl flex-wrap items-end justify-between gap-6 px-4">
    <h2 class="max-w-xl text-4xl tracking-tight text-balance sm:text-5xl">La invitación final</h2>
    <a class="btn" data-variant="primary" data-size="lg" href="/register">Crear cuenta</a>
  </div>
</section>
```

`dark:` variants (the ones inside Basecoat components) only follow `<html class="dark">`;
inside a band, rely on tokens. Check the primary button reads on the dark
surface (`/_design` shows it).

### 2.5 `faq`: details and summary, no JS

```html
<section class="section-y">
  <div class="mx-auto max-w-3xl px-4">
    <div class="accordion">
      <details><summary>Una pregunta real</summary><p>Su respuesta.</p></details>
      <details><summary>Otra pregunta real</summary><p>Su respuesta.</p></details>
    </div>
  </div>
</section>
```

### 2.6 `logo-row`: only with real names

A row of real clients or integrations from `PROJECT.md`. If there are none, do
not make a "trusted by" strip: delete the section.

---

## 3. Textures

Applied sparingly to one or two surfaces, on a decorative layer
(`pointer-events-none`, `aria-hidden`), never on scrolling content.

### 3.1 `grain`: paper and film

```html
<div class="pointer-events-none fixed inset-0 z-30 opacity-[0.05] mix-blend-multiply" aria-hidden="true"
     style="background-image:url(&quot;data:image/svg+xml;utf8,&lt;svg xmlns='http://www.w3.org/2000/svg' width='160' height='160'&gt;&lt;filter id='n'&gt;&lt;feTurbulence type='fractalNoise' baseFrequency='.8' numOctaves='2' stitchTiles='stitch'/&gt;&lt;/filter&gt;&lt;rect width='100%25' height='100%25' filter='url(%23n)'/&gt;&lt;/svg&gt;&quot;)"></div>
```

Allowed by the CSP (`img-src data:`). Fixed and non-interactive; opacity 3-6 %.

### 3.2 `grid`: engineering paper

```html
<section class="relative isolate overflow-hidden py-24">
  <div class="text-border absolute inset-0 -z-10" aria-hidden="true"
       style="background-image:linear-gradient(to right,currentColor 1px,transparent 1px),linear-gradient(to bottom,currentColor 1px,transparent 1px);background-size:3rem 3rem"></div>
  <div class="mx-auto max-w-6xl px-4">…el contenido de la sección…</div>
</section>
```

Colour comes from a token (`text-border`), so it follows light and dark. The
layer needs its section to be `relative isolate overflow-hidden`: without it the
`absolute` layer covers the whole page.

### 3.3 `duotone`: a photo in two colours

```html
<div class="bg-primary relative isolate aspect-[3/2] overflow-hidden rounded-xl">
  <img class="size-full object-cover mix-blend-multiply grayscale contrast-125" src="{{ asset('img/photo.webp') }}" alt="" width="1200" height="800">
</div>
```

The image goes grayscale and multiplies over the brand colour.

### 3.4 `mesh`: a soft colour field

```html
<section class="relative isolate overflow-hidden py-24">
  <div class="absolute inset-0 -z-10" aria-hidden="true"
       style="background:radial-gradient(60% 50% at 20% 20%,color-mix(in oklch,var(--primary) 28%,transparent),transparent),radial-gradient(50% 50% at 85% 70%,color-mix(in oklch,var(--chart-2) 22%,transparent),transparent)"></div>
  <div class="mx-auto max-w-6xl px-4">…el contenido de la sección…</div>
</section>
```

Built from tokens, so it takes the brand and never becomes "AI purple". Same
container rule as `grid`. Keep it behind content that is not scrolling.

---

## 4. Navigation

The header archetypes live in `partials/headers/` and are chosen with
`[structure] header` in `design.toml` (`sticky-blur`, `floating-pill`,
`industrial-rule`, `terminal-bar`, `custom`). Pick by the project's character:

| Header | Reads as | Pairs with |
|---|---|---|
| `sticky-blur` | Quiet, neutral, ubiquitous | minimalista, institucional |
| `floating-pill` | Soft, modern, consumer | suave-premium, orgánico |
| `industrial-rule` | Printed, structured | brutalista, editorial |
| `terminal-bar` | Technical, dense | panel-de-datos, oscuro-tecnológico |
| `custom` | Whatever the signature asks | expresivo, retro |

Beyond the header:

- **Section index (long pages).** A `sticky top-24` column of anchors beside the
  content (`hidden lg:block`); on a phone it disappears and the page keeps its
  headings.
- **Bottom bar (app on a phone).** A `fixed inset-x-0 bottom-0` strip with three
  or four destinations, only below `md:`; add `pb-20` to the page so it does not
  cover content.
- **Back to top.** A plain `<a href="#main">`; no JS, no scroll listener.

Whatever the header, the session (user, logout, login) stays in
`partials/nav_auth.html`. Never rewrite it.
