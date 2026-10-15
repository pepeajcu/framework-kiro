# Panel de datos

**Reads as:** back-office and internal tools: tables, filters, forms, status.
It keeps Basecoat's feel and tightens it. The user is at work, often for hours,
and wants to scan, compare and act quickly.

**Dials:** variance 3, motion 2, density 8.

## Contract

Start from `make design-init preset=panel-de-datos`; the preset writes this:

```toml
[brand]
primary   = "#2563EB"
neutral   = "cool"   # pure | warm | cool | tinted
surface   = "light"   # light | cream | dark | auto
secondary = ""   # opcional: un segundo color de marca
radius    = "0.375rem"

[type]
# Fuentes de Fontsource, siempre locales (woff2 en app/static/fonts/).
# display = { name = "Nombre", weights = [400, 700] }   # titulares
body      = { name = "IBM Plex Sans", weights = [400, 600] }
mono      = { name = "IBM Plex Mono", weights = [400, 500], fallback = "mono" }

[basecoat]
theme = "mira"   # vega | nova | maia | lyra | mira | luma | sera | rhea

[motion]
level = 2   # 1-3 CSS · 4-6 motion.js · 7-8 Motion · 9-10 GSAP

[structure]
header = "terminal-bar"   # sticky-blur | floating-pill | industrial-rule | terminal-bar | ios-bar | custom
density = 8   # 1 aireado ... 10 denso
```

`mira` is the densest Basecoat theme (7-unit controls). `terminal-bar` gives a
compact, high-contrast top bar that does not compete with the data.

## Composition

- A persistent shell: header or `basecoat/sidebar.html.jinja` on the left, page
  title and primary action in a bar under it, content below.
- Tables are the main surface: sticky header, `tabular-nums` on figures
  (`font-mono` or a face with tabular figures), right-aligned numbers,
  zebra-free (use `divide-y`), row hover.
- Filters above the table, as a single row that wraps; the active filters shown
  as removable badges.
- One primary action per screen (`btn primary`), everything else `outline` or
  `ghost`.
- Detail views are two columns: facts on the left (a definition list), history
  or activity on the right.

## States are not optional

Every list and form has **loading** (a skeleton in the shape of the rows),
**empty** (what it is and how to add the first one) and **error** (what failed
and what to try). A panel without them looks finished in the demo and broken in
production.

## Type and colour

- IBM Plex Sans for UI, IBM Plex Mono for ids, dates, amounts. 14 px body is
  normal here.
- A single blue-ish primary; status uses `badge` variants plus an icon or word,
  never colour alone. Reserve `destructive` for destructive actions.
- Cool neutrals, white surface. No decorative colour.

## Motion (level 2)

Only transitions. A toast (Basecoat's) for success. HTMX swaps may use
`htmx-added` / `htmx-settling` classes for a 150 ms highlight of a changed row.

## Avoid

- Hero sections, marketing copy, big illustrations, gradient buttons.
- Cards around everything: a card is for an item, not a layout.
- Truncating data without a way to read it (a `title`, a detail view).

## Signature ideas

A coloured left edge on the active row; keyboard shortcuts shown as `kbd`; a
monospaced status bar at the foot; a tiny sparkline in the header of a column.
