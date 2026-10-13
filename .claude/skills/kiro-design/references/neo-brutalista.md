# Neo-brutalista

**Reads as:** loud, flat colour with thick black borders and hard offset shadows,
big condensed type, deliberately unrefined. Playful where `brutalista` is severe.
For indie products, zines, community projects, anything that wants to feel
human and a little rude.

**Dials:** variance 9, motion 5, density 6.

## Contract

Start from `make design-init preset=neo-brutalista`; the preset writes this:

```toml
[brand]
primary   = "#FACC15"
neutral   = "pure"   # pure | warm | cool | tinted
surface   = "light"   # light | cream | dark
secondary = ""   # opcional: un segundo color de marca
radius    = "0rem"

[type]
# Fuentes de Fontsource, siempre locales (woff2 en app/static/fonts/).
display   = { name = "Big Shoulders Display", weights = [700, 800] }
body      = { name = "Barlow", weights = [400, 600] }
# mono    = { name = "Nombre", weights = [400, 700] }   # código y datos

[basecoat]
theme = "lyra"   # vega | nova | maia | lyra | mira | luma | sera | rhea

[motion]
level = 5   # 1-3 CSS · 4-6 motion.js · 7-8 Motion · 9-10 GSAP

[structure]
header = "industrial-rule"   # sticky-blur | floating-pill | industrial-rule | terminal-bar | custom
```

`lyra` removes every radius. The accent here is a flat yellow: it is a *fill*,
never text (it is about 1.5:1 on white; `make design build` reports it as an
advisory). Buttons carry ink text, which the compiler picks for you.

## Components

Basecoat has no neo-brutalist theme, so the look is a few overrides in
`app/static/css/input.css`, outside the generated blocks:

```css
/* Neo-brutalismo: borde grueso y sombra dura en lo que se pulsa y lo que es una pieza */
.btn,
.card,
.badge,
.input {
  border: 2px solid var(--foreground);
  box-shadow: 4px 4px 0 var(--foreground);
}
.btn:active {
  box-shadow: 0 0 0 var(--foreground);
  translate: 4px 4px;
}
```

Apply it to a few component classes, not to every element, or the effect
becomes noise. Keep the same border width everywhere.

## Composition

- A hard grid with visible rules; tiles in flat colours that do not repeat.
- Oversized condensed headlines in uppercase, tight leading.
- Stickers: a rotated badge (`-rotate-3`) on one or two things.
- Buttons are fat (`btn lg`), labels short and imperative.

## Motion (level 5)

`stagger` on tiles, `marquee` for a ticker, a `reveal` that is quick (the CSS
transition is 0.7 s; keep delays small). Hover moves things by the shadow
width, never fades them.

## Avoid

- Soft shadows, blur, gradients, glass. The only depth is the hard offset.
- Pastel everything: the colours are flat and saturated, and there are few.
- Text on the yellow smaller than 16 px.

## Signature ideas

A different flat colour for every section; a ticker of real news; stickers with
a handwritten label; every link gets an underline that is a thick bar.
