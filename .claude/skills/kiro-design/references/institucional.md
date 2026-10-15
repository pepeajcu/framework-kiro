# Institucional

**Reads as:** an organisation you can trust: public sector, health, education,
finance, a professional body. Plain, high contrast, nothing clever. The design's
job is to get out of the way of the content and signal seriousness.

**Dials:** variance 3, motion 2, density 5. Predictable layout, steady rhythm,
more information per screen than a marketing site.

## Contract

Start from `make design-init preset=institucional`; the preset writes this:

```toml
[brand]
primary   = "#1E3A8A"
neutral   = "cool"   # pure | warm | cool | tinted
surface   = "light"   # light | cream | dark | auto
secondary = ""   # opcional: un segundo color de marca
radius    = "0.375rem"

[type]
# Fuentes de Fontsource, siempre locales (woff2 en app/static/fonts/).
display   = { name = "Source Serif 4", weights = [600, 700], fallback = "serif" }
body      = { name = "Public Sans", weights = [400, 600] }
# mono    = { name = "Nombre", weights = [400, 700] }   # código y datos

[basecoat]
theme = "vega"   # vega | nova | maia | lyra | mira | luma | sera | rhea

[motion]
level = 2   # 1-3 CSS · 4-6 motion.js · 7-8 Motion · 9-10 GSAP

[structure]
header = "sticky-blur"   # sticky-blur | floating-pill | industrial-rule | terminal-bar | ios-bar | custom
```

## Composition

- Two-column layouts with a clear reading order; a sidebar index on long pages.
- Heroes are short: a headline, a sentence, the main task as a button. `split`
  with a real photograph, never an abstract illustration.
- Generous, even spacing. Cards only for things that are genuinely items;
  everything else is a rule (`divide-y`) or plain space.
- Every page states where you are (breadcrumb, `h1`) and what to do next.

## Type and colour

- A serif display (Source Serif 4) for headings and a humanist sans (Public
  Sans) for text. Body at 16-18 px, line length 60-70 characters.
- Cool neutrals and one deep, desaturated primary (navy, forest). White surface.
- Contrast is not a target to scrape past: aim for 7:1 on body text.
- Links are underlined, always. Focus rings are never removed.

## Accessibility is the style

WCAG AA is the floor and the design leans on it: visible focus, 44 px touch
targets, `lang` set, no information carried by colour alone, forms with
labels above fields and errors in text. Use the Spanish a person would use
(`Presentar solicitud`, not `Submit`).

## Motion (level 2)

None beyond CSS transitions (hover, focus). A page that needs scroll animation
to be understood has the wrong content.

## Avoid

- Stock-photo handshakes, a "trusted by" strip with invented logos, a badge
  ("Nuevo") in the hero.
- Decorative gradients, glass, glow, rounded-everything.
- Clever microcopy. Say what it is.

## Signature ideas

A coloured rule under every `h1`; a crest-like wordmark in the header; a fixed
"last updated" line under every page title; numbered sections for long
documents.
