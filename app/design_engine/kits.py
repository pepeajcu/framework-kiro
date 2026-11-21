"""Platform kits: a look that is more than colours.

A preset sets colour, radius, type and theme. A **kit** adds what makes a platform
feel like itself: its own type scale, its materials, its list and control shapes.
`[structure] kit = "ios"` compiles the iOS kit into `input.css`, between the markers
`kiro:kit`; the components that use it are `components/ios.html.jinja`, and the
header is `partials/headers/ios-bar.html`.

What the iOS kit takes from Apple's Human Interface Guidelines, and what it does not:

- **Type scale** of Dynamic Type at its default size (17 px body, 34 px large title).
  The font is the platform's own, San Francisco, through the system stack; Apple does
  not allow a site to ship it, so everyone else gets the local Inter
  (`fallback = "system"`, see `fonts.py`).
- **Margins** of 16 px on a phone and 20 px wider, controls of at least 44 px,
  separators inset by 16 px, concentric radii.
- **Materials** (translucent bars and sheets) only on the navigation and controls
  layer: a bar, a tab bar, a sheet. Never on content that scrolls. A solid surface
  replaces them where `backdrop-filter` is missing and when the person asks for less
  transparency or more contrast. Safari ignores `prefers-reduced-transparency`, so the
  compiler computes the **least opacity that keeps the text at AA over a white and over
  a black backdrop** (`--kit-material-alpha`) instead of trusting the preference.
- **Not taken:** SVG displacement ("liquid glass" refraction), which only Chromium
  renders; Apple's private `-apple-visual-effect`; SF Symbols (licence).

Colours are always tokens: the kit contains no hex and follows whatever `design.toml`
compiled, light, dark or `auto`.
"""

from __future__ import annotations

from app.branding import contrast_ratio
from app.design_engine.blocks import render_block
from app.design_engine.contract import DesignError, Kit
from app.design_engine.palette import AA, Palette, token_rgb

#: Opacity steps tried, lowest first. Below 50 % a "material" is mostly the backdrop.
_FLOOR, _STEP = 0.50, 0.01
#: The thick material is this much more opaque than the regular one.
THICK_EXTRA = 0.12


def _mix(
    foreground: tuple[float, float, float], backdrop: float, alpha: float
) -> tuple[float, ...]:
    """`foreground` at `alpha` over a grey `backdrop` (0 black, 1 white), in sRGB."""
    return tuple(alpha * channel + (1 - alpha) * backdrop for channel in foreground)


def material_alpha(background: str, foreground: str) -> float:
    """The least opacity at which `foreground` text reads (AA) on `background` as a
    translucent layer over *any* backdrop, tested over the two extremes, white and black.
    """
    bg, fg = token_rgb(background), token_rgb(foreground)
    alpha = _FLOOR
    while alpha < 1.0:
        mixed = [_mix(bg, backdrop, alpha) for backdrop in (0.0, 1.0)]
        if all(contrast_ratio(fg, color) >= AA for color in mixed):  # type: ignore[arg-type]
            return round(alpha, 2)
        alpha += _STEP
    return 1.0


def _percent(alpha: float) -> str:
    return f"{round(alpha * 100)}%"


def _alphas(tokens: dict[str, str]) -> tuple[str, str]:
    regular = material_alpha(tokens["--background"], tokens["--foreground"])
    return _percent(regular), _percent(min(1.0, regular + THICK_EXTRA))


def _declarations(alphas: tuple[str, str], indent: str = "  ") -> str:
    regular, thick = alphas
    return f"{indent}--kit-material-alpha: {regular};\n{indent}--kit-material-alpha-thick: {thick};"


def _tokens(palette: Palette) -> str:
    light, dark = _alphas(palette.light), _alphas(palette.dark)
    rows = [f":root {{\n{_declarations(light)}\n}}"]
    if not palette.dark_only:
        rows.append(f".dark {{\n{_declarations(dark)}\n}}")
    if palette.auto:
        rows.append(
            "@media (prefers-color-scheme: dark) {\n"
            f"  :root {{\n{_declarations(dark, '    ')}\n  }}\n}}"
        )
    return "\n\n".join(rows)


IOS_CSS = """\
/* ---- Escala tipográfica: Dynamic Type de Apple HIG al tamaño por defecto ---- */
html {
  -webkit-text-size-adjust: 100%;
  -webkit-tap-highlight-color: transparent;
}
body {
  font-size: 1.0625rem;
  line-height: 1.2941;
}
/* 17 px en los campos: por debajo de 16 px, Safari en iOS hace zoom al enfocarlos. */
:where(input, select, textarea) {
  font-size: 1.0625rem;
}
.ios-large-title,
.ios-title-1,
.ios-title-2,
.ios-title-3,
.ios-headline,
.ios-callout,
.ios-subhead,
.ios-footnote,
.ios-caption {
  margin: 0;
}
.ios-large-title {
  font-size: 2.125rem;
  line-height: 1.2059;
  font-weight: 700;
  letter-spacing: 0.011em;
}
.ios-title-1 { font-size: 1.75rem; line-height: 1.2143; font-weight: 700; letter-spacing: 0.007em; }
.ios-title-2 { font-size: 1.375rem; line-height: 1.2727; font-weight: 700; }
.ios-title-3 { font-size: 1.25rem; line-height: 1.25; font-weight: 600; }
.ios-headline { font-size: 1.0625rem; line-height: 1.2941; font-weight: 600; }
.ios-callout { font-size: 1rem; line-height: 1.3125; }
.ios-subhead { font-size: 0.9375rem; line-height: 1.3333; }
.ios-footnote { font-size: 0.8125rem; line-height: 1.3846; }
.ios-caption { font-size: 0.75rem; line-height: 1.3333; }
.ios-secondary { color: var(--muted-foreground); }

/* ---- Márgenes y fondo agrupado (el gris de Ajustes) ---- */
:root {
  --ios-radius-inner: max(calc(var(--radius) - 0.5rem), 0.25rem);
}
.ios-page {
  padding-inline: 1rem;
}
@media (min-width: 768px) {
  .ios-page { padding-inline: 1.25rem; }
}
.ios-grouped {
  background-color: var(--muted);
  min-height: 100dvh;
}

/* ---- Lista agrupada ---- */
.ios-group { margin-block: 1.5rem; }
.ios-group-header,
.ios-group-footer {
  margin: 0;
  padding-inline: 1rem;
  color: var(--muted-foreground);
  font-size: 0.8125rem;
  line-height: 1.3846;
}
.ios-group-header { margin-bottom: 0.375rem; text-transform: uppercase; letter-spacing: 0.02em; }
.ios-group-footer { margin-top: 0.375rem; }
.ios-list {
  list-style: none;
  margin: 0;
  padding: 0;
  overflow: hidden;
  border-radius: var(--radius);
  background-color: var(--card);
  color: var(--card-foreground);
}
.ios-row {
  position: relative;
  display: flex;
  align-items: center;
  gap: 0.75rem;
  min-height: 2.75rem;
  padding: 0.625rem 1rem;
  color: inherit;
  text-decoration: none;
}
/* El separador empieza a 16 px del borde, como en iOS, y no cruza el icono. */
.ios-list > li + li > .ios-row::before {
  content: "";
  position: absolute;
  top: 0;
  right: 0;
  left: 1rem;
  border-top: 1px solid var(--border);
}
.ios-row-label { flex: 1; min-width: 0; }
.ios-row-detail { color: var(--muted-foreground); }
.ios-row-chevron { flex: none; width: 0.5rem; height: 0.875rem; color: var(--muted-foreground); }
.ios-row[data-destructive] .ios-row-label { color: var(--destructive); }
a.ios-row:active,
button.ios-row:active {
  background-color: color-mix(in oklab, var(--foreground) 8%, transparent);
}

/* ---- Control segmentado ---- */
.ios-segmented {
  display: inline-flex;
  gap: 2px;
  padding: 2px;
  border: 0;
  border-radius: var(--ios-radius-inner);
  background-color: color-mix(in oklab, var(--foreground) 8%, transparent);
}
.ios-segmented label {
  position: relative;
  display: inline-flex;
  flex: 1;
  align-items: center;
  justify-content: center;
  min-height: 2rem;
  padding-inline: 0.75rem;
  border-radius: calc(var(--ios-radius-inner) - 2px);
  font-size: 0.8125rem;
  font-weight: 500;
  cursor: pointer;
}
.ios-segmented input {
  position: absolute;
  inset: 0;
  margin: 0;
  opacity: 0;
  cursor: pointer;
}
.ios-segmented label:has(input:checked) {
  background-color: var(--background);
  font-weight: 600;
  box-shadow: 0 1px 3px color-mix(in oklab, var(--foreground) 20%, transparent);
}
.ios-segmented label:has(input:focus-visible) {
  outline: 2px solid var(--ring);
  outline-offset: 2px;
}

/* ---- Materiales: solo en navegación y controles, nunca en contenido que se desplaza ---- */
.material-regular,
.material-thick {
  background-color: var(--background);
}
@supports (backdrop-filter: blur(1px)) or (-webkit-backdrop-filter: blur(1px)) {
  .material-regular {
    background-color: color-mix(in oklab, var(--background) var(--kit-material-alpha), transparent);
    -webkit-backdrop-filter: blur(20px) saturate(180%);
    backdrop-filter: blur(20px) saturate(180%);
  }
  .material-thick {
    background-color: color-mix(
      in oklab,
      var(--background) var(--kit-material-alpha-thick),
      transparent
    );
    -webkit-backdrop-filter: blur(30px) saturate(180%);
    backdrop-filter: blur(30px) saturate(180%);
  }
}
@media (prefers-reduced-transparency: reduce), (prefers-contrast: more) {
  .material-regular,
  .material-thick {
    background-color: var(--background);
    -webkit-backdrop-filter: none;
    backdrop-filter: none;
  }
}

/* ---- Barra superior ---- */
.ios-bar {
  border-bottom: 1px solid var(--border);
}

/* ---- Barra de pestañas: abajo en móvil, no existe en pantallas anchas ---- */
.ios-tabbar {
  position: fixed;
  inset-inline: 0;
  bottom: 0;
  z-index: 40;
  display: flex;
  border-top: 1px solid var(--border);
  padding-bottom: env(safe-area-inset-bottom);
}
.ios-tabbar a {
  display: flex;
  flex: 1;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.125rem;
  min-height: 3.0625rem;
  color: var(--muted-foreground);
  font-size: 0.625rem;
  line-height: 1.2;
  text-decoration: none;
}
.ios-tabbar svg { width: 1.5rem; height: 1.5rem; }
/* El color de la marca va en el icono; el texto, en el color de lectura. */
.ios-tabbar a[aria-current="page"] { color: var(--foreground); font-weight: 600; }
.ios-tabbar a[aria-current="page"] svg { color: var(--primary); }
body:has(.ios-tabbar) { padding-bottom: calc(3.0625rem + env(safe-area-inset-bottom)); }
@media (min-width: 768px) {
  .ios-tabbar { display: none; }
  body:has(.ios-tabbar) { padding-bottom: 0; }
}

/* ---- Hoja modal ---- */
.ios-sheet {
  width: min(100%, 40rem);
  max-height: 90dvh;
  margin: auto auto 0;
  padding: 0 0 env(safe-area-inset-bottom);
  border: 0;
  border-radius: calc(var(--radius) * 1.75) calc(var(--radius) * 1.75) 0 0;
  background-color: var(--card);
  color: var(--card-foreground);
}
.ios-sheet::backdrop { background-color: oklch(0 0 0 / 0.35); }
.ios-sheet::before {
  content: "";
  display: block;
  width: 2.25rem;
  height: 0.3125rem;
  margin: 0.5rem auto;
  border-radius: 9999px;
  background-color: color-mix(in oklab, var(--muted-foreground) 50%, transparent);
}
@media (min-width: 768px) {
  .ios-sheet { margin: auto; border-radius: calc(var(--radius) * 1.75); }
}

/* ---- Respuesta al toque ---- */
.btn:active { transform: scale(0.97); }
"""


def render_kit_block(kit: Kit, palette: Palette) -> str | None:
    """The `kiro:kit` block for `kit`, or None when there is none to compile."""
    if kit == "none":
        return None
    if kit != "ios":  # pragma: no cover - the contract only admits the kits above
        raise DesignError(f"el kit '{kit}' no existe")
    return render_block("kit", f"{_tokens(palette)}\n\n{IOS_CSS}")
