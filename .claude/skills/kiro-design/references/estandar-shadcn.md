# Estándar shadcn

**Reads as:** the Basecoat look the framework ships with, chosen on purpose:
neutral greys, the classic shadcn component shapes, no signature of its own.

**Dials:** variance 2, motion 3, density 5.

This is the one style that is not a distinct identity, and it exists for one
reason: *generic is allowed, but only if you ask for it.* A project that never
chose anything ends up here by accident and `make design-check` says so. A
project that chose it says so in `design.toml`, and the check stops raising the
generic-pattern warnings (`P1` to `P10`) while still listing them as allowed on
every run. The floor does not move: contrast, touch size and performance apply
exactly as in any other style.

Pick it when the product is an internal tool, a prototype, or a client that asked
for "the standard shadcn look". Do **not** pick it to avoid deciding.

## Contract

Start from `make design-init preset=estandar-shadcn`; the preset writes this:

```toml
[brand]
primary   = "#171717"
neutral   = "pure"   # pure | warm | cool | tinted
surface   = "light"   # light | cream | dark | auto
secondary = ""   # opcional: un segundo color de marca
radius    = "0.625rem"

[type]
# Fuentes de Fontsource, siempre locales (woff2 en app/static/fonts/).
# display = { name = "Nombre", weights = [400, 700] }   # titulares
# body    = { name = "Nombre", weights = [400, 700] }   # texto
# mono    = { name = "Nombre", weights = [400, 700] }   # código y datos

[basecoat]
theme = "vega"   # vega | nova | maia | lyra | mira | luma | sera | rhea

[motion]
level = 3   # 1-3 CSS · 4-6 motion.js · 7-8 Motion · 9-10 GSAP

[structure]
header = "sticky-blur"   # sticky-blur | floating-pill | industrial-rule | terminal-bar | ios-bar | custom

[rules]
allow = ["P1", "P10", "P2", "P3", "P4", "P5", "P6", "P7", "P8", "P9"]   # reglas de gusto permitidas a propósito (ver DESIGN.md)
```

Record in `DESIGN.md`, under *Decisiones de diseño*, that the generic look was
requested and by whom, and keep `[rules] allow` to the patterns the project
actually uses: remove the ones it does not.

## Composition

- Centred container (`layouts/app.html`), a ruled list or a table before a grid
  of cards, Basecoat components as they come.
- The `sticky-blur` header. One accent: the near-black primary on a button.

## Avoid

- Choosing this style and then adding decoration to hide that it is generic: pick
  another style instead.
- Treating the allowed patterns as a template to fill. They are permitted, not
  recommended.
