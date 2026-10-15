# Retro / Y2K

**Reads as:** the web of 1999-2003 seen with affection: electric blue, silver,
bevels and glints, pixel type, chunky rounded shapes, a little irony. For
games, music, nostalgic brands, a personal site with attitude.

**Dials:** variance 8, motion 6, density 4.

## Contract

Start from `make design-init preset=retro-y2k`; the preset writes this:

```toml
[brand]
primary   = "#2F5BFF"
neutral   = "tinted"   # pure | warm | cool | tinted
surface   = "light"   # light | cream | dark | auto
secondary = ""   # opcional: un segundo color de marca
radius    = "1.5rem"

[type]
# Fuentes de Fontsource, siempre locales (woff2 en app/static/fonts/).
display   = { name = "Pixelify Sans", weights = [400, 700] }
body      = { name = "Rubik", weights = [400, 500] }
mono      = { name = "Silkscreen", weights = [400], fallback = "mono" }

[basecoat]
theme = "luma"   # vega | nova | maia | lyra | mira | luma | sera | rhea

[motion]
level = 6   # 1-3 CSS · 4-6 motion.js · 7-8 Motion · 9-10 GSAP

[structure]
header = "floating-pill"   # sticky-blur | floating-pill | industrial-rule | terminal-bar | ios-bar | custom
density = 4   # 1 aireado ... 10 denso
```

## Composition

- Windowed panels: a card with a title bar (`header` with a darker strip) and
  small controls drawn as spans, like an old OS dialog.
- Bevels and gloss done with tokens, never an image:

```css
/* Un brillo de cristal sobre un botón o panel */
.y2k-gloss {
  background-image: linear-gradient(
    to bottom,
    color-mix(in oklch, white 55%, transparent),
    transparent 55%
  );
}
```

- Starbursts and sparkles as small inline SVG, one stroke weight.
- A visitor counter, a "best viewed in" line, a guestbook link: only if the
  project can honour them with real content.

## Type and colour

- Pixelify Sans for headlines and Silkscreen for tiny labels (both pixel
  faces). Rubik for body. Keep pixel type large: it is unreadable under 14 px.
- Tinted cool neutrals, an electric blue primary, silver surfaces. A single
  secondary accent (hot pink) for stickers is allowed.

## Motion (level 6)

`marquee` for a banner, `reveal` with a small distance. Blink and shake are
decorative; wrap them in `motion-safe:` and never on anything that carries
information.

## Avoid

- Dark mode neon cliché; "vaporwave" gradients; purple. This is cheerful, not
  moody.
- Low-resolution raster art: use SVG so it stays crisp on HiDPI.
- Copy in the style of a teenager's page unless the brand really talks like that.

## Signature ideas

A "window" frame around the hero; a scrolling status bar; a pixel cursor trail
(CSS only, behind `motion-safe`); a dithered gradient background made as an SVG
pattern.
