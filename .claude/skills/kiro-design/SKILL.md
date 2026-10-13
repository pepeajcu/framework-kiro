---
name: kiro-design
description: How to give a Kiro project its own visual identity instead of the default Basecoat look. Reads DESIGN.md (style, signature, archetypes) and design.toml (the compiled contract: colour, fonts, theme, header, motion level), applies the anti-slop rules from taste-skill, and checks the result at /_design. Use whenever building or restyling a page, a layout, the header, a landing, or when the user mentions design, branding, colours, style, fonts, animation, logo or "it all looks the same".
---

# Design in Kiro

Basecoat gives every project the same neutral grey shadcn look. That is the
right *starting point* and the wrong *finish*. This skill is how a project stops
looking like every other one.

The method comes from [taste-skill](https://github.com/Leonxlnx/taste-skill)
(MIT); five of its skills are vendored in `references/`. This file adapts them to
our stack. If they disagree, **this file wins**: they assume React/Framer/CDN
fonts, we have Jinja, HTMX and Tailwind with no Node.

## The idea in one paragraph

An identity here has two halves. **`design.toml`** is what a machine can apply:
brand colour, the temperature of the greys, light/cream/dark surface, radius,
fonts, Basecoat theme, header archetype and motion level. `make design build`
compiles it to CSS, local fonts and scripts, and `make design-check` verifies it.
**`DESIGN.md`** is what a person (and you) must decide: tone, references, the
dials, the archetypes and, above all, the **signature**: two or three gestures
the project commits to repeating. The contract can be filled from a catalogue;
the signature cannot, which is exactly why two projects of the same style stay
different.

## Step 0: read, then state

1. Read `DESIGN.md` and `design.toml`. If `DESIGN.md` still has `TODO`, **stop
   and ask the user to run `/kiro-init`**. Do not invent a brand.
2. If `design.toml` is still the default (`make design-check` says so), the
   project has no identity yet: the same advice applies.
3. State the **Design Read** in one line before writing markup:
   *"Reading this as: \<page kind> for \<audience>, \<style> language, dials
   V/M/D = x/y/z, signature: \<gestures>."*
4. Only then build.

## How an identity is applied

```
 /kiro-init ──► design.toml ──► make design build ──► input.css blocks + fonts + motion
                                                           │
 DESIGN.md (signature, archetypes) ──► your templates      ▼
                                                    make css ──► /_design ──► /kiro-design-review
```

| You want to | Command |
|---|---|
| Start from a style (changes theme, radius, greys, surface, fonts, header, motion) | `make design-init preset=<style> [primary="#hex"]` |
| Set the brand colour, greys, surface, secondary, radius | `make brand-colors primary="#hex" [neutral=warm] [surface=cream] [secondary="#hex"] [radius=0.5rem]` |
| Add a font (downloads the woff2, validates it) | `make font name="Fraunces" weights="400,600" role=display` |
| Change theme, header or motion level | `make design-set v="basecoat.theme=rhea structure.header=floating-pill motion.level=6"` |
| Re-apply everything from `design.toml` | `make design build` (idempotent; `make design watch` rebuilds on save) |
| Look at it | `make dev`, then open `/_design` |
| Verify the contract matches the project | `make design-check` |
| Set the logo | `make logo src=<path or URL>` |

Every command rewrites `design.toml` and rebuilds; nothing else edits
`input.css` between the `kiro:*` markers, and those blocks are regenerated on
every build, so **never edit inside them**. Your own CSS goes outside the markers.
Never edit `app/static/css/vendor/` or `app/templates/basecoat/` either.

## The three dials

Every decision is gated by three numbers, 1-10. `DESIGN.md` records them;
`motion.level` in `design.toml` equals `MOTION_INTENSITY`, and `make design-check`
warns when they differ.

| Dial | 1 | 10 |
|---|---|---|
| `DESIGN_VARIANCE` | perfect symmetry | artsy chaos |
| `MOTION_INTENSITY` | static | cinematic |
| `VISUAL_DENSITY` | gallery, airy | cockpit, packed |

## Style presets

The user picks one in `/kiro-init`; each is a *starting contract* for every axis
at once (so a lazy fill still lands somewhere distinct) and points to a reference
to read before building. `make design-init preset=<name>` writes it.

| Style | V / M / D | Reads as | Theme | Header | Radius | Fonts | Reference |
|---|---|---|---|---|---|---|---|
| `minimalista` | 5 / 3 / 2 | Notion, Linear: monocromo cálido, tipografía editorial, bordes finos | `nova` | `sticky-blur` | 0.5rem | Newsreader + Geist | `references/minimalist.md` |
| `suave-premium` | 7 / 6 / 3 | Calmado y caro: sombras suaves, tarjetas anidadas, mucho aire | `luma` | `floating-pill` | 1rem | Fraunces + Plus Jakarta Sans | `references/soft.md` |
| `brutalista` | 9 / 4 / 6 | Imprenta suiza o terminal: rejilla dura, tipografía enorme, un acento de peligro | `lyra` | `industrial-rule` | 0rem | Archivo Black + Archivo + JetBrains Mono | `references/brutalist.md` |
| `institucional` | 3 / 2 / 5 | Confianza primero: sector público, salud, finanzas. Llano y de alto contraste | `vega` | `sticky-blur` | 0.375rem | Source Serif 4 + Public Sans | `references/institucional.md` |
| `expresivo` | 9 / 8 / 3 | Agencia, creativo, lanzamiento: tipografía grande, asimetría y movimiento | `rhea` | `custom` | 1.5rem | Bricolage Grotesque + Figtree | `references/expresivo.md` |
| `panel-de-datos` | 3 / 2 / 8 | Back-office denso: conserva el tacto de Basecoat y aprieta la densidad | `mira` | `terminal-bar` | 0.375rem | IBM Plex Sans + IBM Plex Mono | `references/panel-de-datos.md` |
| `editorial` | 6 / 3 / 3 | Una publicación impresa: serif de titular, columna estrecha, reglas finas | `sera` | `industrial-rule` | 0rem | Playfair Display + Public Sans | `references/editorial.md` |
| `organico` | 6 / 5 / 2 | Cálido y hecho a mano: formas blandas, tierra y verdes, serif amable | `maia` | `floating-pill` | 1.25rem | Young Serif + Figtree | `references/organico.md` |
| `neo-brutalista` | 9 / 5 / 6 | Color plano y chillón, bordes gruesos, sombras duras, tipografía condensada | `lyra` | `industrial-rule` | 0rem | Big Shoulders Display + Barlow | `references/neo-brutalista.md` |
| `retro-y2k` | 8 / 6 / 4 | Web de 1999 con ironía: azul eléctrico, píxeles, brillos y bordes redondos | `luma` | `floating-pill` | 1.5rem | Pixelify Sans + Rubik + Silkscreen | `references/retro-y2k.md` |
| `oscuro-tecnologico` | 6 / 5 / 6 | Herramienta de desarrollo: superficie oscura, monoespaciada, un acento frío | `mira` | `terminal-bar` | 0.375rem | Martian Mono + Hanken Grotesk | `references/oscuro-tecnologico.md` |

Open the matching reference before building. The user may mix two or describe
their own: then write the real values in `design.toml` and say so in `DESIGN.md`.
Presets are for **public pages**; authenticated screens inherit the same tokens
but sit one notch more dense and one notch calmer than the landing.

### What each Basecoat theme actually is

Measured from the vendored CSS, not guessed. The theme is the biggest single
lever on how components *feel*, so it is the first thing a preset sets.

| Theme | Buttons | Cards | Character |
|---|---|---|---|
| `vega` | 36 px, `rounded-md` | `rounded-xl`, hairline | The classic shadcn baseline |
| `nova` | 32 px, `rounded-lg` | `rounded-xl`, no shadow | Compact, modern, quiet |
| `maia` | 36 px, pill | `rounded-2xl` | Soft, friendly, generous |
| `lyra` | 32 px, square | `rounded-none` | Boxy, technical, sharp |
| `mira` | 28 px, `rounded-md` | `rounded-lg` | The densest: data and tools |
| `luma` | 36 px, pill | `rounded-4xl` + shadow | Very soft and premium |
| `sera` | 40 px, square, wide padding | `rounded-none`, shadow | Uppercase tracked labels: print |
| `rhea` | 32 px, `rounded-2xl` | `rounded-3xl` | Bubbly and bold |

## Mapping the brief onto the engine

Nothing is hand-coloured in templates. Identity lives in tokens, so one change
restyles every component.

| `DESIGN.md` says | Where it goes |
|---|---|
| Primary / secondary colour | `[brand] primary`, `secondary` (`make brand-colors`) |
| Warm, cool, pure or brand-tinted greys | `[brand] neutral = warm \| cool \| pure \| tinted`. **One temperature per project.** |
| Light, paper-cream or dark | `[brand] surface = light \| cream \| dark`. `dark` is dark-only (no toggle to maintain) |
| Corner radius | `[brand] radius`. One scale, everywhere |
| Fonts | `[type] display \| body \| mono` (`make font`) |
| How components feel | `[basecoat] theme` (table above) |
| The shape of the header | `[structure] header` (see Structure) |
| How much it moves | `[motion] level` (see Motion) |
| Logo | `app/static/brand/logo.svg` or `.png`, shown by `brand_mark.html` through `brand_logo()` |

The compiler derives all ~30 Basecoat colour tokens, light and dark, from those
few decisions and **solves the text colours for WCAG AA** instead of eyeballing
them. If a brand colour cannot carry a button label, it stops and proposes the
nearest hex that can. The brand colour as *text* (links, `btn link`) is reported
as an advisory: a yellow brand is fine as a fill, not as body text.

## Structure: layouts, headers and dark bands

Pages do not extend `base.html`; they extend a layout:

| Layout | For | Container |
|---|---|---|
| `layouts/app.html` | Private screens, lists, forms, auth, errors | Centred, `max-w-5xl`; `{% set page_width = "max-w-3xl" %}` changes it |
| `layouts/landing.html` | Home, landings, anything with sections | None: each `<section>` places `<div class="mx-auto max-w-6xl px-4">` **inside** itself |

`landing.html` also asks for the motion scripts of the project's level. If a page
overrides `{% block scripts %}`, it must call `{{ super() }}`.

The **header** is chosen with `[structure] header`: `sticky-blur` (quiet),
`floating-pill` (soft), `industrial-rule` (printed), `terminal-bar` (technical)
or `custom` (`partials/headers/custom.html` is the project's own; keep its two
includes, `brand_mark.html` and `nav_auth.html`). The session logic (user,
logout POST with CSRF, login links) lives in `partials/nav_auth.html` and is
shared by all of them: restyle the shape, never rewrite the logic.

A **dark band** in a light page is `<section class="dark bg-background
text-foreground">`: the compiler re-maps every token under `.dark`. (`dark:`
variants inside Basecoat components follow only `<html class="dark">`; inside a
band rely on tokens.)

`pages/home.html` is **scaffolding, not a model**: a headline, a paragraph and a
ruled list on purpose. Do not copy "badge + title + three cards"; build the real
page from the archetypes below and `DESIGN.md`.

## Variance: what keeps two projects apart

1. **Signature (mandatory).** `DESIGN.md` names two or three gestures: "headlines
   in 12vw serif that bleed off the edge", "everything mono and uppercase with
   one acid accent", "a hairline grid that is always visible". Repeat them on
   every page. They come from the project, never from a catalogue.
2. **Archetypes.** `references/archetypes.md`: seven heroes (`split`,
   `type-giant`, `bento`, `editorial`, `marquee`, `sticky-stack`,
   `horizontal-pan`), sections, textures and navigation, each with working markup
   and its mobile fallback. Record the chosen ones under **Arquetipos**.
3. **Type pairings.** `references/type-pairings.md`: 25 pairs, all installable
   with `make font`.
4. **Do not repeat a layout.** Three image+text zigzags in a row is one too many;
   vary the archetype between sections.

## Fonts: local, from Fontsource (ADR-0005)

The CSP is `font-src 'self'`; a Google Fonts `<link>` fails silently. Use
`make font`: it checks the family and weights exist on Fontsource, downloads the
Latin woff2, validates it, and writes `@font-face` and the tokens. Display
(`h1`-`h3`) and body are separate roles. Satoshi, Cabinet Grotesk and General
Sans are **not** on Fontsource; pick from `type-pairings.md`.

Up to three roles (display, body, mono), at most two weights each. The body
font is preloaded automatically.

## Anti-slop rules (adapted from taste-skill)

These are what make a page look generated. Break them only when `DESIGN.md`
says so.

**Colour**
- One accent, saturation under 80 %. Neutral base. Lock it: the accent in the
  hero is the accent in the footer.
- No default "AI purple" glow, no neon gradients. Purple is fine **if the brand
  colour is purple**, and then with intent.
- Never pure `#000` on pure `#fff`. The compiler's neutrals are off-black.
- One palette temperature per project: do not mix warm and cool greys.

**Type**
- Not Inter/Roboto/Arial by default. `type-pairings.md` has 25 alternatives. Inter
  only if the brief asks for neutral or the audience is `institucional`.
- A serif needs a reason: the style (editorial, organico, institucional,
  suave-premium) or the brand names one. "It feels premium" is not a reason.
- Emphasis inside a headline = italic or bold of the **same** family.
- Body at most 65 characters wide (`max-w-prose`). Display: `tracking-tight`,
  tight leading, but leave room for descenders.

**Layout**
- Centred hero over a gradient, then three equal cards: banned as a default.
  With `DESIGN_VARIANCE > 4`, prefer split or asymmetric compositions.
- The hero fits the first viewport: headline max 2 lines, subtext max 20 words,
  one primary CTA and at most one secondary. No logo wall, no trust strip, no
  pricing teaser inside it.
- Eyebrow labels (small uppercase tag above a heading): at most one per three
  sections.
- Cards only when elevation means something. Otherwise `border-t`, `divide-y`,
  or space.
- Pick **one** radius scale and keep it (it is in `design.toml`).
- Never `h-screen`; use `min-h-[100dvh]`.
- Every multi-column layout declares its `< 768px` fallback in the same element.

**Content**
- No "John Doe", "Acme", "Lorem ipsum", no round fake numbers (`99.99%`,
  `10,000+`). Use the real domain from `PROJECT.md`.
- No emoji in markup. Icons are SVG, one stroke weight throughout.
- Ban the vocabulary: *Elevate, Seamless, Unleash, Next-Gen, Game-changer, Delve*.
- One label per CTA intent. "Contact us" and "Get in touch" are the same CTA twice.
- **No em dashes in user-facing copy.** Use a comma, a colon, or two sentences.

**Visuals**
- The hero has a real visual or is deliberately type-only (`type-giant`,
  `editorial`). A `div` pretending to be a screenshot is neither.
- Images are local: SVG, or photos under `app/static/img/`. The CSP
  (`img-src 'self' data:`) blocks `picsum.photos`, Unsplash and any other host;
  a placeholder that works in the upstream skills silently fails here.
- Always `width` and `height` (no layout shift), `alt` that says what it is (or
  `alt=""` when decorative), `loading="lazy"` below the fold.

**States and a11y** (not optional)
- Every list, form and fetch has its **loading** (a skeleton shaped like the
  result, not a spinner), **empty** (says how to fill it) and **error** state.
- Text contrast WCAG AA: 4.5:1 body, 3:1 large. The compiler guarantees it for
  the palette; check any pairing you invent (`/_design` shows the ratios).
- Label above the input. Never placeholder-as-label.
- Buttons show `:active` feedback and a visible focus ring.
- `backdrop-blur` only on fixed or sticky bars, never on scrolling content.

## Motion: attributes, never JavaScript

The page writes `data-motion` attributes; `[motion] level` in `design.toml`
decides which ones do anything. A page **never** contains its own animation
script. Content is complete without JS, and with `prefers-reduced-motion`
nothing moves: that is guaranteed by the engine (hidden states exist only under
the `js-motion` class the script sets), but it only holds if you do not hide
content yourself.

| Level | Engine | Weight | Values |
|---|---|---|---|
| 1-3 | CSS transitions | 0 | none: `hover:`, `active:`, `focus-visible:` |
| 4-6 | `motion.js` (ours) | 3.4 KB gz | `reveal`, `stagger`, `split-reveal`, `count`, `marquee` |
| 7-8 | + Motion One 10 (vendored) | +11 KB gz | + `parallax`, `progress`, `data-motion-ease="spring"` |
| 9-10 | GSAP + ScrollTrigger (vendored) | +48 KB gz | + `pin`, `scrub`, `horizontal` (replaces Motion) |

`make design build` downloads the library a level needs, pinned by version and
SHA-256, and writes `app/static/js/vendor/NOTICE.md`. GSAP's licence is its own
(free for commercial use, not for tools that compete with Webflow's visual
builder); the framework does not redistribute it, each project downloads it.

```html
<h1 data-motion="split-reveal">Words rise one by one</h1>
<p  data-motion="reveal" data-motion-delay="0.2">Fades up when it enters.</p>
<ul data-motion="stagger" data-motion-delay="0.08"> <li>…</li> </ul>
<span data-motion="count" data-motion-to="1280">1.280</span>
<div  data-motion="marquee" data-motion-speed="30"> <span>…</span> </div>
<div  data-motion="parallax" data-motion-distance="40">…</div>            <!-- 7+ -->
<section data-motion="horizontal"> <div class="flex w-max">…</div> </section> <!-- 9+ -->
```

Rules:
- `split-reveal` needs a plain-text element (an element with tags inside stays
  static). `count` wraps **only the number**; the server text is what it ends on.
- Do not put `reveal` on the LCP image or the element that is the largest
  contentful paint: it would not paint until the script runs.
- Level above what the project has? The attribute is ignored and the content
  just shows. `make design-check` lists every attribute above the level.
- `pin` and `horizontal` act only from 768 px; on a phone the content flows.
- Motion only on `transform` and `opacity`; never an animation on a scrolling
  surface with `backdrop-blur`.
- HTMX is handled: fragments are armed on swap and their triggers cleaned up.
- `/_design` has a **Movimiento** section that demonstrates exactly the values
  your level provides.

## The logo

- Lives in `app/static/brand/`, named `logo.svg` or `logo.png` (PNG must be
  square, 1:1). SVG is preferred: it scales.
- Import it with `make logo src="<path or URL>"`. The script validates it
  (square PNG, SVG without scripts) and refuses anything else.
- Never hard-code the file name in a template. `brand_mark.html` uses
  `brand_logo()`; it returns the URL or `None`, and the header falls back to the
  project name.
- `references/brandkit.md` is the checklist for judging a logo (a clear idea,
  sparse, one symbol, works small). Kiro does not generate images; if there is
  no logo, ship the name and say it can be added later.

## The perception loop

You cannot judge a design you have not seen.

1. After any identity change: `make design build`, then `make dev`, then open
   **`/_design`** (tokens with contrast, type scale, components, a test hero,
   light and dark, motion). `/_design?style=<preset>` previews a palette without
   writing anything.
2. After building a page: run **`/kiro-design-review`**: it captures 375 px and
   1280 px, compares against `DESIGN.md` and the anti-slop list, asks "does this
   look like the default template?" and fixes it in at most two passes.
3. For an app that already exists: **`/kiro-redesign`**.
4. Before saying "done": `make design-check` and `make check`.

## Before you say "done"

- [ ] Design Read stated; dials and signature taken from `DESIGN.md`
- [ ] `make design-check` has no errors; `design.toml` and `DESIGN.md` agree
- [ ] No hard-coded colour in a template: only tokens (`bg-primary`,
      `text-muted-foreground`, …)
- [ ] One accent, one radius scale, one temperature of grey
- [ ] Fonts are local woff2 installed with `make font`; nothing from a CDN
- [ ] The page extends the right layout; the header is an archetype, not a rewrite
      of the session logic
- [ ] An archetype chosen on purpose; no repeated section layout; eyebrows within limit
- [ ] The signature appears on this page
- [ ] Hero fits the viewport and has a real visual (or is type-only on purpose)
- [ ] Loading, empty and error states exist
- [ ] Motion is `data-motion` only; nothing above the project's level; nothing hidden
      without the engine's gate
- [ ] Contrast checked; focus ring visible; reduced motion respected
- [ ] Checked at 375 px and at 1280 px, light and dark
- [ ] No em dashes, no emoji, no placeholder names in the copy
- [ ] Logo renders in the header and as favicon (if the project has one)
