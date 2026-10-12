---
name: kiro-design
description: How to give a Kiro project its own visual identity instead of the default Basecoat look. Reads DESIGN.md (brand colours, style, logo), applies the anti-slop rules from taste-skill, and maps everything onto Basecoat tokens. Use whenever building or restyling a page, a layout, the header, a landing, or when the user mentions design, branding, colours, style, logo or "it all looks the same".
---

# Design in Kiro

Basecoat gives every project the same neutral grey shadcn look. That is the
right *starting point* and the wrong *finish*. This skill is how a project stops
looking like every other one.

The method comes from [taste-skill](https://github.com/Leonxlnx/taste-skill)
(MIT). Three of its skills are vendored in `references/`; this file adapts the
rest to our stack. If they disagree, **this file wins**: they assume
React/Framer/CDN fonts, we have Jinja, HTMX and Tailwind with no Node.

## Step 0 — read `DESIGN.md`, always

`DESIGN.md` at the repo root is the design brief, the way `PROJECT.md` is the
domain brief. Before touching any template:

1. Read `DESIGN.md`. If it still has `TODO`, **stop and ask the user to run
   `/kiro-init`** (or fill the design section by hand). Do not invent a brand.
2. State the **Design Read** in one line before writing markup:
   *"Reading this as: \<page kind> for \<audience>, \<style> language, dials
   V/M/D = x/y/z, accent \<colour>."*
3. Only then build.

## The three dials

Every decision is gated by three numbers, 1–10. `DESIGN.md` records them.

| Dial | 1 | 10 |
|---|---|---|
| `DESIGN_VARIANCE` | perfect symmetry | artsy chaos |
| `MOTION_INTENSITY` | static | cinematic |
| `VISUAL_DENSITY` | gallery, airy | cockpit, packed |

## Style presets

The user picks one in `/kiro-init`. Each maps to dials and to a reference.

| Style | V / M / D | Reads as | Reference |
|---|---|---|---|
| `minimalista` | 5 / 3 / 2 | Notion, Linear. Warm monochrome, editorial type, hairline borders | `references/minimalist.md` |
| `suave-premium` | 7 / 6 / 3 | Calm, expensive. Soft shadows, nested cards, whitespace | `references/soft.md` |
| `brutalista` | 9 / 4 / 6 | Swiss print or terminal. Rigid grid, huge type, one hazard accent | `references/brutalist.md` |
| `institucional` | 3 / 2 / 5 | Trust-first: public sector, health, finance. Plain, high contrast | taste-skill §1.A |
| `expresivo` | 9 / 8 / 3 | Agency, creative, consumer launch. Big type, asymmetry, motion | taste-skill §1.A |
| `panel-de-datos` | 3 / 2 / 8 | Admin, back-office. Keeps Basecoat's feel, tightens density | Kiro addition |

Open the matching reference before building. For `institucional`, `expresivo`
and `panel-de-datos` there is no file: the dials and the rules below are the
spec.

The presets are for **public pages**. Authenticated screens (tables, forms)
inherit the same tokens but should sit one notch more dense and one notch
calmer than the landing.

## Mapping the brief onto Basecoat

Nothing is hand-coloured in templates. Identity lives in tokens, so one change
restyles every component.

| `DESIGN.md` says | Where it goes |
|---|---|
| Brand colours | `make brand-colors primary="#hex"` writes the `kiro:brand` block in `app/static/css/input.css` (`--primary`, `--ring`, light and `.dark`) |
| Corner radius | `--radius` in that same block. One scale, everywhere |
| Fonts | `--font-sans` / `--font-display` in `@theme` in `input.css` |
| Logo | `app/static/brand/logo.svg` or `logo.png`. Shown by `partials/header.html` through `brand_logo()` |
| Whole look | Switch the Basecoat theme import (`vega` `nova` `maia` `lyra` `mira` `luma` `sera` `rhea`) |

Then `make css`. Never edit `app/static/css/vendor/` or `app/templates/basecoat/`.

### Fonts: vendor them, never a CDN (ADR-0005)

The CSP is `font-src 'self'`. A Google Fonts `<link>` will silently fail.

1. Download the `.woff2` once (Fontsource ships them: `https://cdn.jsdelivr.net/fontsource/fonts/<name>@latest/latin-400-normal.woff2`)
   into `app/static/fonts/`.
2. Declare `@font-face` in `input.css` with `font-display: swap`.
3. Point `--font-sans` at it in `@theme`.

Ship at most two families (one sans or display, one mono if needed) and two
weights each.

## Anti-slop rules (adapted from taste-skill)

These are what make a page look generated. Break them only when `DESIGN.md`
says so.

**Colour**
- One accent, saturation under 80 %. Neutral base. Lock it: the accent used in
  the hero is the accent in the footer.
- No default "AI purple" glow, no neon gradients. Purple is fine **if the brand
  colour is purple** — then do it with intent.
- Never pure `#000` on pure `#fff`. Off-black text, tinted shadows.
- One palette temperature per project: do not mix warm and cool greys.

**Type**
- Not Inter/Roboto/Arial as the default. Prefer Geist, Outfit, Satoshi,
  Cabinet Grotesk, Plus Jakarta Sans. Inter only if the brief asks for neutral
  or the audience is `institucional`.
- No serif "because it feels premium". Serif only if the brand names one or the
  style is genuinely editorial.
- Emphasis inside a headline = italic or bold of the **same** family.
- Body at most 65 characters wide (`max-w-prose`). Display: `tracking-tight`,
  tight leading, but leave room for descenders.

**Layout**
- Centred hero over a gradient, then three equal cards: banned as a default.
  With `DESIGN_VARIANCE > 4`, prefer split or asymmetric compositions.
- The hero fits the first viewport: headline max 2 lines, subtext max 20
  words, one primary CTA and at most one secondary. No logo wall, no trust
  strip, no pricing teaser inside it.
- Do not repeat a section layout. Three image+text zigzags in a row is one too
  many.
- Eyebrow labels (small uppercase tag above a heading): at most one per three
  sections.
- Cards only when elevation means something. Otherwise `border-t`, `divide-y`,
  or space.
- Pick **one** radius scale (sharp, soft or pill) and keep it.
- Never `h-screen`; use `min-h-[100dvh]`.
- Every multi-column layout declares its `< 768px` fallback in the same
  component.

**Content**
- No "John Doe", "Acme", "Lorem ipsum", no round fake numbers (`99.99%`,
  `10,000+`). Use the real domain from `PROJECT.md`.
- No emoji in markup. Icons are SVG, one stroke weight throughout.
- Ban the vocabulary: *Elevate, Seamless, Unleash, Next-Gen, Game-changer,
  Delve*.
- One label per CTA intent. "Contact us" and "Get in touch" on one page are
  the same CTA twice.
- **No em dashes in user-facing copy.** Use a comma, a colon, or two sentences.

**States and a11y** (not optional)
- Every list, form and fetch has its **loading** (skeleton shaped like the
  result, not a spinner), **empty** (says how to fill it) and **error** state.
- Text contrast WCAG AA: 4.5:1 body, 3:1 large. `make brand-colors` prints the
  ratio for the button text; check any other pairing you invent.
- Label above the input. Never placeholder-as-label.
- Buttons show `:active` feedback (`active:scale-[0.98]`) and a visible focus
  ring.
- Motion only on `transform` and `opacity`. Wrap it in
  `@media (prefers-reduced-motion: no-preference)`.
- Scroll reveals use `IntersectionObserver`, never a `scroll` listener.
- `backdrop-blur` only on fixed or sticky bars, never on scrolling content.

## Motion without a framework

No GSAP, no Framer. At `MOTION_INTENSITY <= 4` CSS transitions and a
`@starting-style` / `IntersectionObserver` fade-up are enough. Above that, ask
before vendoring a library (ADR-0005 applies). HTMX swaps can animate with
`htmx-added` / `htmx-settling` classes.

## The logo

- Lives in `app/static/brand/`, named `logo.svg` or `logo.png` (PNG must be
  square, 1:1). SVG is preferred: it scales and takes the theme.
- Import it with `make logo src="<path or URL>"`. The script validates it
  (square PNG, SVG without scripts), copies it, and refuses anything else.
- Never hard-code the file name in a template. Use `brand_logo()`; it returns
  the URL or `None`, and the header falls back to the project name.
- Use it in the header, the favicon and the email layout. Next to the project name it is decorative
  (`alt=""`); alone, give it the name as `alt`. Always a fixed size so the
  layout does not shift.

## Before you say "done"

Run through this list, then `make css` and `make check`.

- [ ] Design Read stated, dials taken from `DESIGN.md`
- [ ] No hard-coded colour in a template: only tokens (`bg-primary`,
      `text-muted-foreground`, …)
- [ ] One accent, one radius scale, one temperature of grey
- [ ] Fonts are local `.woff2`, nothing from a CDN
- [ ] Hero fits the viewport; no repeated section layout; eyebrows within limit
- [ ] Loading, empty and error states exist
- [ ] Contrast checked; focus ring visible; reduced motion respected
- [ ] Checked at 375 px and at 1280 px, light and dark
- [ ] No em dashes, no emoji, no placeholder names in the copy
- [ ] Logo renders in the header and as favicon (if the project has one)
