# Expresivo

**Reads as:** an agency site or a launch page. The type is the picture, the layout
is asymmetric and the page moves. Everything is turned up, and one thing is
turned up *most*. Use it for creative studios, events, consumer launches, a
portfolio. Do not use it for anything where people come to get a job done.

**Dials:** variance 9, motion 8, density 3. Lots of air around very large things.

## Contract

Start from `make design-init preset=expresivo`; the preset writes this:

```toml
[brand]
primary   = "#EA580C"
neutral   = "tinted"   # pure | warm | cool | tinted
surface   = "cream"   # light | cream | dark
secondary = ""   # opcional: un segundo color de marca
radius    = "1.5rem"

[type]
# Fuentes de Fontsource, siempre locales (woff2 en app/static/fonts/).
display   = { name = "Bricolage Grotesque", weights = [600, 800] }
body      = { name = "Figtree", weights = [400, 600] }
# mono    = { name = "Nombre", weights = [400, 700] }   # código y datos

[basecoat]
theme = "rhea"   # vega | nova | maia | lyra | mira | luma | sera | rhea

[motion]
level = 8   # 1-3 CSS · 4-6 motion.js · 7-8 Motion · 9-10 GSAP

[structure]
header = "custom"   # sticky-blur | floating-pill | industrial-rule | terminal-bar | custom
```

`header = "custom"` is deliberate: an expressive site's header is part of the
signature. `partials/headers/custom.html` starts as a copy of `sticky-blur`;
rewrite it (a logo that is huge, a menu that is a single word, a sticky corner
mark), keeping the two includes (`brand_mark.html`, `nav_auth.html`).

## Composition

- Heroes: `type-giant`, or `split` with the visual overlapping the headline.
  Break the grid on purpose: one element pulled out by a negative margin, one
  headline that crosses the column gutter.
- Sections alternate in *scale*, not just in background: a full-bleed statement,
  then a tight list, then an oversized number.
- Rotate or offset exactly one element per section, never every one.
- Use `dark-band` once to change the weather halfway down the page.

## Type and colour

- A display face with presence (Bricolage Grotesque, Syne, Unbounded) at 8-14vw
  in the hero; `tracking-tighter`, `leading-[0.9]`. Body stays calm.
- `neutral = "tinted"` + `surface = "cream"` gives a coloured paper. The accent
  is a saturated colour; check the button label reads (AA) on `/_design`.
- A secondary colour is welcome here: set `secondary` and use `btn secondary`.

## Motion (level 8)

`split-reveal` on every hero headline, `stagger` on grids, `marquee` for a
band, `parallax` on one or two images, `data-motion-ease="spring"` on cards.
Level 9 adds `pin` and `scrub` if the page earns a set piece. Never animate the
element that is the LCP image; give the headline `split-reveal` instead.

## Avoid

- Everything moving at once. If three things animate in the first screen, two
  of them are noise.
- Centred hero + gradient + three cards: this is the default look this engine
  exists to prevent.
- Low-contrast pastel text on the tinted paper. Run `make design-check`.

## Signature ideas (pick two or three, invent your own)

A headline that is cropped by the viewport edge; a number so large it is a
background; a cursor-sized accent shape that follows content; one word in a
different face, italic, in every headline; a hard offset shadow on exactly the
primary button.
