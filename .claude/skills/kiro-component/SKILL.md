---
name: kiro-component
description: How to build UI in a Kiro project with Basecoat components — the data-variant API, which components need Jinja macros, and how to customise without breaking updates. Use when adding or styling any UI element.
---

# UI components in Kiro

The design system is [Basecoat](https://basecoatui.com): shadcn/ui implemented
in plain HTML + Tailwind. It is vendored into this repo (see `docs/vendor.md`).

## Variants are `data-*` attributes, not classes

This is the single most common mistake. Basecoat 1.0 dropped modifier classes.
Writing `btn-primary` produces an **unstyled button with no error** — nothing
warns you.

```html
<!-- correct -->
<button class="btn" data-variant="primary">Save</button>
<button class="btn" data-variant="outline" data-size="sm">Cancel</button>
<button class="btn" data-variant="destructive">Delete</button>
<span class="badge" data-variant="secondary">Draft</span>

<!-- WRONG -->
<button class="btn-primary">Save</button>
<button class="btn btn-outline btn-sm">Cancel</button>
```

- Variants: `primary` `secondary` `outline` `ghost` `link` `destructive`
- Sizes: `xs` `sm` `default` `lg` `icon` `icon-xs` `icon-sm` `icon-lg`

## Two kinds of component

**CSS-only** — just write the markup with the class. Most components:
`btn` `card` `badge` `alert` `input` `textarea` `label` `field` `table`
`avatar` `breadcrumb` `progress` `skeleton` `kbd` `item` `empty` `switch`
`checkbox` `radio` `tooltip` `button-group` `input-group`.

```html
<article class="card">
  <header>
    <h2>Title</h2>
    <p>Supporting text</p>
  </header>
  <section>Body</section>
  <footer><button class="btn" data-variant="primary">Action</button></footer>
</article>
```

**Macro-driven** — nine components need JavaScript and ship a Jinja macro in
`app/templates/basecoat/`: `select` `combobox` `command` `dialog`
`dropdown-menu` `popover` `sidebar` `tabs` `toast`.

```jinja
{% from "basecoat/select.html.jinja" import select %}

{{ select(
  name="city",
  placeholder="Choose a city",
  items=[
    {"value": "mad", "label": "Madrid"},
    {"value": "bcn", "label": "Barcelona"},
  ]
) }}
```

Open the macro file to see its parameters — each one documents them at the top.

## Finding the right class

Do not guess. Grep the vendored source:

```bash
ls app/static/css/vendor/basecoat/components/     # every component
grep -oE "\.btn\[data-variant='[a-z]+'\]" app/static/css/vendor/basecoat/styles/vega.css | sort -u
```

## Customising without breaking updates

**Never edit `app/static/css/vendor/` or `app/templates/basecoat/`.** Those are
overwritten when Basecoat is updated. Instead:

- Design tokens (colours, fonts, radius) → `@theme` block in
  `app/static/css/input.css`
- A reusable project-specific component → `app/templates/components/`, built out
  of Basecoat classes
- Switching the whole look → change the theme import in `input.css`:
  `vega` `nova` `maia` `lyra` `mira` `luma` `sera` `rhea`

## After any template change

```bash
make css
```

Tailwind only emits classes it finds in the files listed under `@source` in
`input.css`. A class you just wrote will be missing from `app.css` until you
rebuild.
