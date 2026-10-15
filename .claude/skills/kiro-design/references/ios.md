# iOS

**Reads as:** an Apple interface on the web: translucent bars, grouped lists, a
type scale that is not the browser's, controls you can hit with a thumb, and light
or dark following the device. It is a **kit**, not a colour scheme: the shapes of
the components change, not only the paint.

**Dials:** variance 3, motion 5, density 4. Calm and regular; the motion is a short
press response and a sheet, not choreography.

## Two ways to use it

- **A landing in the style of apple.com**: `layouts/landing.html`, a large title,
  generous type, one accent, sections that breathe. Use the type classes
  (`ios-large-title`, `ios-title-1`...) and the `material-regular` header; skip the
  tab bar and the grouped lists.
- **An app in the style of iOS**: `layouts/app.html` on the grouped background
  (`ios-grouped`), `large_title`, `grouped_list` and `list_row` for settings and
  lists, `segmented` for filters, `tab_bar` for the sections on a phone, `sheet` for
  an action that needs a screen of its own.

## Contract

Start from `make design-init preset=ios`; the preset writes this:

```toml
[brand]
primary   = "#0066CC"
neutral   = "cool"   # pure | warm | cool | tinted
surface   = "auto"   # light | cream | dark | auto
secondary = ""   # opcional: un segundo color de marca
radius    = "0.75rem"

[type]
# Fuentes de Fontsource, siempre locales (woff2 en app/static/fonts/).
# display = { name = "Nombre", weights = [400, 700] }   # titulares
body      = { name = "Inter", weights = [400, 600], fallback = "system" }
# mono    = { name = "Nombre", weights = [400, 700] }   # código y datos

[basecoat]
theme = "maia"   # vega | nova | maia | lyra | mira | luma | sera | rhea

[motion]
level = 5   # 1-3 CSS · 4-6 motion.js · 7-8 Motion · 9-10 GSAP

[structure]
header = "ios-bar"   # sticky-blur | floating-pill | industrial-rule | terminal-bar | ios-bar | custom
kit    = "ios"   # none | ios
density = 4   # 1 aireado ... 10 denso
```

- `kit = "ios"` compiles the kit into `input.css` (the `kiro:kit` block): the type
  scale, the list, segmented, tab-bar and sheet shapes, the materials. Edit nothing
  inside it; override outside the markers.
- `surface = "auto"`: light by default, dark when the device asks, with no switch for
  people to maintain. Components with `dark:` variants follow it too (the variant is
  redefined, no script).
- `fallback = "system"`: `font-family` is `-apple-system, BlinkMacSystemFont, "Inter",
  sans-serif`. Apple devices render **San Francisco** and download nothing; every
  other device gets the local Inter. Apple's licence does not let a site ship San
  Francisco, and `system-ui` is deliberately not in the list (it would win on Windows
  and Android and Inter would never be used).
- The primary is **`#0066CC`**, not Apple's system blue (`#007AFF`): white text on
  `#007AFF` is 4.0:1 and the compiler would refuse it for a button. `#0066CC` gives 5.3:1
  and is the blue of apple.com's links. Use the system blue only for non-text accents.

## The numbers (Apple Human Interface Guidelines)

| Style | Size / leading | Weight | Class |
|---|---|---|---|
| Large title | 34 / 41 | bold | `ios-large-title` |
| Title 1 | 28 / 34 | bold | `ios-title-1` |
| Title 2 | 22 / 28 | bold | `ios-title-2` |
| Title 3 | 20 / 25 | semibold | `ios-title-3` |
| Headline | 17 / 22 | semibold | `ios-headline` |
| Body | 17 / 22 | regular | (the page default) |
| Callout | 16 / 21 | regular | `ios-callout` |
| Subhead | 15 / 20 | regular | `ios-subhead` |
| Footnote | 13 / 18 | regular | `ios-footnote` |
| Caption | 12 / 16 | regular | `ios-caption` |

- **Touch targets** 44 x 44 pt (never under 28). The kit keeps every row, tab and field
  at 44 px or more, and the compiled floor (`kiro:a11y`) enlarges the pressable area of
  buttons on a phone.
- **Margins** 16 px on a phone and 20 px wider (`ios-page`). Separators start 16 px in
  from the edge and do not cross the icon.
- **Radii are concentric**: an inner corner is the outer one minus the padding between
  them (`--ios-radius-inner`).
- **Contrast** 4.5:1 for text, 3:1 for large text. The compiler guarantees it for the
  palette in light and dark.

## Materials (the "glass")

Apple's guidance, which this kit follows exactly: a translucent material belongs to the
**navigation and controls layer** (a bar, a tab bar, a sheet, a popover), never to content
that scrolls. Use `material-regular` on a fixed or sticky bar and `material-thick` where
more separation is needed.

- Over `backdrop-filter` the bar is the page colour at `--kit-material-alpha` (computed
  by the compiler as the least opacity that keeps the text at AA over a white and over a
  black backdrop), blurred 20 px and saturated.
- Without `backdrop-filter`, with `prefers-reduced-transparency: reduce` or
  `prefers-contrast: more`, it is a **solid** page colour. Safari ignores the first, so the
  computed opacity, not the preference, is what makes it readable there.
- At most three or four glass layers on screen, and never animate the blur.
- **Not done on purpose:** the SVG displacement filters that fake refraction (only
  Chromium renders them), Apple's private `-apple-visual-effect`, and SF Symbols (licence).
  Draw icons as SVG with one stroke weight.

## Components

```jinja
{% from "components/ios.html.jinja" import large_title, grouped_list, list_row, segmented, tab_bar, sheet, sheet_trigger %}

<div class="ios-grouped">
  {{ large_title("Ajustes") }}
  {% call grouped_list(header="Cuenta", footer="Se aplica en todos tus dispositivos.") %}
    {{ list_row("Perfil", detail=user.full_name, href="/perfil", chevron=True) }}
    {{ list_row("Cerrar sesión", destructive=True) }}
  {% endcall %}
  {{ segmented("vista", "Vista", [{"value": "lista", "label": "Lista"}, {"value": "mapa", "label": "Mapa"}], selected="lista") }}
</div>
```

All of it is plain HTML that works without JavaScript. The sheet is a native `<dialog>`:
`sheet_trigger` opens it, a `method="dialog"` form closes it. Pass user data freely:
text and attributes are escaped; only an `icon` (your own `<svg>`) is marked safe.

## Avoid

- A tab bar on a desktop layout (it hides itself from 768 px: use the header).
- Glass on a card or a list that scrolls, or stacked glass.
- Apple's system blue behind white text.
- Emoji or SF Symbols as icons.
- Calling it "iOS" and keeping a three-cards-in-a-row landing: the kit gives the
  components, `DESIGN.md` still needs a signature and an archetype.

## Signature ideas

- "Every list is a grouped list on the grey background, with the section header in
  small capitals above it."
- "A large title on every screen that collapses into the bar's own title."
- "One sheet per task: nothing that needs more than a form opens a new page."
