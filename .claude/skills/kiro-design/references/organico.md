# Orgánico

**Reads as:** warm, tactile, human: food, craft, wellbeing, local business, small
farms and makers. Soft shapes, earth and green, a friendly serif. The opposite
of sharp and corporate.

**Dials:** variance 6, motion 5, density 2.

## Contract

Start from `make design-init preset=organico`; the preset writes this:

```toml
[brand]
primary   = "#4D7C0F"
neutral   = "warm"   # pure | warm | cool | tinted
surface   = "cream"   # light | cream | dark | auto
secondary = ""   # opcional: un segundo color de marca
radius    = "1.25rem"

[type]
# Fuentes de Fontsource, siempre locales (woff2 en app/static/fonts/).
display   = { name = "Young Serif", weights = [400], fallback = "serif" }
body      = { name = "Figtree", weights = [400, 600] }
# mono    = { name = "Nombre", weights = [400, 700] }   # código y datos

[basecoat]
theme = "maia"   # vega | nova | maia | lyra | mira | luma | sera | rhea

[motion]
level = 5   # 1-3 CSS · 4-6 motion.js · 7-8 Motion · 9-10 GSAP

[structure]
header = "floating-pill"   # sticky-blur | floating-pill | industrial-rule | terminal-bar | ios-bar | custom
density = 2   # 1 aireado ... 10 denso
```

`maia` has pill buttons and generous radii; `radius = "1.25rem"` makes the
rest of the shapes match.

## Composition

- Blobs and arches as image masks (`rounded-t-full`, `rounded-[3rem]`), never
  perfect rectangles for photography. Photos are warm and real: the product,
  the hands, the place.
- Sections overlap by a few rem (negative margins) so there are no hard seams.
- A narrow, calm column for text; lots of vertical space.
- Hand-drawn touches as small inline SVG (an underline, a leaf), one stroke
  weight and used sparingly.

## Type and colour

- Young Serif for headlines (single weight, so no `font-bold`), Figtree for
  text. Sentence case, no uppercase tracking.
- Warm neutrals on a cream surface; a deep green primary; earthy secondary
  tones (terracotta, ochre) only as fills.
- Paper texture with `grain` at 3 % at most.

## Motion (level 5)

Slow and soft: `reveal` and `stagger`, `data-motion-delay` around 0.1-0.2 s.
No bounce. A gentle `parallax` on a photograph (level 7) is allowed.

## Avoid

- Stock "natural" imagery (a leaf on a white background), green gradients, a
  fake-hand font for body text.
- Sharp corners anywhere a corner is visible.
- Mixing warm and cool greys.

## Signature ideas

Every photo in a different organic mask; a handwritten signature SVG at the end
of the page; seasonal colour swaps made in `design.toml`; a recipe-card
treatment for the main content type.
