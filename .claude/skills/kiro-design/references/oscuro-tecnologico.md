# Oscuro-tecnológico

**Reads as:** a developer tool or a technical product: a dark surface, a
monospaced voice, one cold accent, precise spacing. For CLIs, APIs, infrastructure,
security, data tools, a game studio's tech blog.

**Dials:** variance 6, motion 5, density 6.

## Contract

Start from `make design-init preset=oscuro-tecnologico`; the preset writes this:

```toml
[brand]
primary   = "#38BDF8"
neutral   = "cool"   # pure | warm | cool | tinted
surface   = "dark"   # light | cream | dark
secondary = ""   # opcional: un segundo color de marca
radius    = "0.375rem"

[type]
# Fuentes de Fontsource, siempre locales (woff2 en app/static/fonts/).
display   = { name = "Martian Mono", weights = [400, 700], fallback = "mono" }
body      = { name = "Hanken Grotesk", weights = [400, 600] }
# mono    = { name = "Nombre", weights = [400, 700] }   # código y datos

[basecoat]
theme = "mira"   # vega | nova | maia | lyra | mira | luma | sera | rhea

[motion]
level = 5   # 1-3 CSS · 4-6 motion.js · 7-8 Motion · 9-10 GSAP

[structure]
header = "terminal-bar"   # sticky-blur | floating-pill | industrial-rule | terminal-bar | custom
```

`surface = "dark"` makes the whole site dark: the engine puts the dark palette on
`:root` and the `dark` class on `<html>`, so there is no flash and no toggle to
maintain. The accent is kept as chosen and lifted only where it would vanish.

## Composition

- A hero with a command or a snippet in a real `<pre>` (copyable), not a
  screenshot. A `terminal-bar` header repeats the idea.
- Dense feature lists with monospaced labels; a bento of small, precise tiles.
- A visible grid (`grid` texture) or hairline borders (`border-border` is a
  faint white on dark) instead of shadows.
- Code blocks, `kbd`, tables and status badges are first-class citizens.

## Type and colour

- Martian Mono (or JetBrains Mono) for display and figures, Hanken Grotesk for
  text. Mono headlines at a modest size: they are wide.
- Near-black with a faint cool tint, off-white text (never `#fff` on `#000`), one
  accent (sky) and one signal colour for success/danger.
- Glow is allowed once, on the accent, as a faint `box-shadow` of the brand
  colour at 20 % opacity. A page full of glow is the cliché to avoid.

## Motion (level 5)

`reveal`, `stagger` for lists, `count` for numbers, a typing effect is not in
the vocabulary: if you want one, write it as a CSS `steps()` animation behind
`motion-safe`, once.

## Avoid

- Matrix rain, purple-to-blue gradients, neon on everything, fake terminal
  output that says nothing real.
- Light-grey text on dark below 4.5:1: `make design build` checks it for you.
- Low-contrast borders on interactive elements (focus must be obvious).

## Signature ideas

A blinking cursor after the main headline; a status line at the foot with the
real build or version; section titles as file paths (`/docs/api`); a command
palette hint (`kbd`) in the header.
