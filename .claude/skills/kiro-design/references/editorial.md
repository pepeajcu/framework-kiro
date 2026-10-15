# Editorial

**Reads as:** a printed publication. Long text is the product: a magazine, a
journal, a blog that is taken seriously, a cultural institution. Hierarchy comes
from type size and rules, not from boxes.

**Dials:** variance 6, motion 3, density 3.

## Contract

Start from `make design-init preset=editorial`; the preset writes this:

```toml
[brand]
primary   = "#7F1D1D"
neutral   = "warm"   # pure | warm | cool | tinted
surface   = "cream"   # light | cream | dark | auto
secondary = ""   # opcional: un segundo color de marca
radius    = "0rem"

[type]
# Fuentes de Fontsource, siempre locales (woff2 en app/static/fonts/).
display   = { name = "Playfair Display", weights = [700], fallback = "serif" }
body      = { name = "Public Sans", weights = [400, 600] }
# mono    = { name = "Nombre", weights = [400, 700] }   # código y datos

[basecoat]
theme = "sera"   # vega | nova | maia | lyra | mira | luma | sera | rhea

[motion]
level = 3   # 1-3 CSS · 4-6 motion.js · 7-8 Motion · 9-10 GSAP

[structure]
header = "industrial-rule"   # sticky-blur | floating-pill | industrial-rule | terminal-bar | ios-bar | custom
density = 3   # 1 aireado ... 10 denso
```

`sera` is the Basecoat theme with square corners and uppercase, tracked labels:
the closest to print. `industrial-rule` gives the masthead its heavy rule.

## Composition

- A narrow reading column (`max-w-3xl`, about 65 characters) with the headline
  allowed to be wider than the text beneath it.
- Hero `editorial`: kicker line, headline, standfirst, a byline row between two
  hairlines. Pull quotes break the column on both sides.
- A grid of articles is a list with a thumbnail and a date, divided by rules
  (`numbered` section), not a wall of cards.
- Drop caps, section marks and footnotes are real, small HTML, not images.

## Type and colour

- A serif display (Playfair Display 700) in sentence case at large sizes with
  `tracking-tight`; the sans (Public Sans) for UI and captions only. Body in
  the serif if the reading is long: declare it as the `body` role instead.
- Cream paper, near-black ink, one deep accent (oxblood). Rules are 1 px, in
  `border-border`, and heavier (`border-b-2`) only under the masthead.
- Numerals: use old-style or tabular figures deliberately (`font-variant-numeric`).

## Motion (level 3)

None to speak of. A reading-progress bar (`data-motion="progress"`) needs
level 7 and suits long articles.

## Avoid

- Boxes with shadows; a sticky blur header; emoji; "Read more" on a card that
  could be a plain link in the headline.
- Justified text without hyphenation (`hyphens-auto`, `lang` set).
- A hero image behind text unless it is darkened enough to pass contrast.

## Signature ideas

Small caps for the kicker; a section number in the margin; a coloured first
word in every headline; a date set in monospaced type; marginal notes on wide
screens that fold into the text on a phone.
