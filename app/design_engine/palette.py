"""Derive the complete Basecoat palette from a handful of decisions.

`app.branding.brand_tokens` only ever produced three variables, so a project's
background, text, cards, borders and muted tones stayed Basecoat's neutral grey
and *any* change of structure still read as "the same grey app". This module
derives all of them (about thirty tokens, light and dark) from:

    primary    the brand colour
    neutral    the temperature of every grey: pure | warm | cool | tinted
    surface    light | cream | dark
    secondary  an optional second brand colour

Two rules shape every number below:

1. **Colours are solved, not eyeballed.** Text tokens start from Basecoat's own
   value and move only as far as needed to reach WCAG AA against every
   background they are used on. A palette that cannot read is not returned.
2. **Defaults are Basecoat's.** `pure` + `light` reproduces Basecoat's neutral
   greys, so choosing a brand colour alone changes the accent and nothing else.

Pure functions: nothing here reads a file or the environment.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal

from app.branding import (
    BRAND_BLOCK_END,
    BRAND_BLOCK_START,
    DARK_BACKGROUND,
    BrandTokens,
    brand_tokens,
    contrast_ratio,
    foreground_for,
    format_oklch,
    oklch_to_rgb,
    parse_hex,
    rgb_to_oklch,
)
from app.design_engine.contract import Brand, DesignError

Rgb = tuple[float, float, float]

# WCAG AA for normal-size text is 4.5:1. The 0.1 margin absorbs the rounding of
# oklch() to three decimals and the difference between our sRGB clamp and the
# gamut mapping a browser applies.
AA = 4.5
TARGET = 4.6

_WARM_HUE = 80.0
_COOL_HUE = 255.0
_WARM_CHROMA = 0.010
_COOL_CHROMA = 0.008


@dataclass(frozen=True)
class Colour:
    """An OKLCH colour, rounded to what actually gets written into the CSS."""

    lightness: float
    chroma: float
    hue: float
    alpha: float | None = None

    @staticmethod
    def of(lightness: float, chroma: float, hue: float, alpha: float | None = None) -> Colour:
        # The same precision `format_oklch` prints, so the contrast we measure
        # is the contrast the browser will render.
        return Colour(round(lightness, 3), round(max(chroma, 0.0), 3), round(hue % 360, 1), alpha)

    def css(self) -> str:
        return format_oklch(self.lightness, self.chroma, self.hue, self.alpha)

    @property
    def rgb(self) -> Rgb:
        return oklch_to_rgb(self.lightness, self.chroma, self.hue)


@dataclass(frozen=True)
class ContrastPair:
    """One text/background pairing and whether it reads."""

    mode: Literal["light", "dark"]
    foreground: str
    background: str
    ratio: float
    required: bool

    @property
    def ok(self) -> bool:
        return self.ratio >= AA

    def describe(self) -> str:
        return f"{self.foreground} sobre {self.background}, modo {_MODE_ES[self.mode]}"


_MODE_ES = {"light": "claro", "dark": "oscuro"}


@dataclass(frozen=True)
class Palette:
    """Every token for `:root` and for `.dark`, plus the contrast audit."""

    light: dict[str, str]
    dark: dict[str, str]
    dark_only: bool
    pairs: tuple[ContrastPair, ...]
    warnings: tuple[str, ...]
    #: `surface = "auto"`: light by default, dark when the system asks (no selector).
    auto: bool = False

    @property
    def failures(self) -> tuple[ContrastPair, ...]:
        """Required pairs below AA: a palette with any of these must not ship."""
        return tuple(p for p in self.pairs if p.required and not p.ok)

    @property
    def advisories(self) -> tuple[ContrastPair, ...]:
        """Optional pairs below AA (the brand colour used as text, for instance)."""
        return tuple(p for p in self.pairs if not p.required and not p.ok)


# --- Helpers ----------------------------------------------------------------


def format_ratio(ratio: float, decimals: int = 2) -> str:
    """A contrast ratio, truncated rather than rounded.

    Rounding would print a failing 4.4999 as "4.50" next to a minimum of 4.5.
    """
    factor = 10**decimals
    return f"{math.floor(ratio * factor) / factor:.{decimals}f}"


def rgb_to_hex(rgb: Rgb) -> str:
    r, g, b = (round(min(max(c, 0.0), 1.0) * 255) for c in rgb)
    return f"#{r:02X}{g:02X}{b:02X}"


def neutral_axis(brand: Brand) -> tuple[float, float]:
    """`(hue, chroma)` shared by every grey of the project.

    One axis for the whole palette is the "one temperature per project" rule
    made mechanical: a warm background can never end up with cool borders.
    """
    neutral = brand.neutral
    if neutral == "pure" and brand.surface == "cream":
        neutral = "warm"  # a cream paper is warm by definition
    if neutral == "pure":
        return 0.0, 0.0
    if neutral == "warm":
        return _WARM_HUE, _WARM_CHROMA
    if neutral == "cool":
        return _COOL_HUE, _COOL_CHROMA
    _, primary_chroma, primary_hue = rgb_to_oklch(parse_hex(brand.primary))
    return primary_hue, min(max(primary_chroma * 0.10, 0.006), 0.02)


def _solve(
    start: float,
    chroma: float,
    hue: float,
    against: list[Rgb],
    *,
    darker: bool,
    minimum: float = TARGET,
) -> float:
    """Move a lightness from `start` until it clears `minimum` on every background."""
    step = -0.005 if darker else 0.005
    lightness = start
    while True:
        candidate = Colour.of(lightness, chroma, hue).rgb
        if min(contrast_ratio(candidate, bg) for bg in against) >= minimum:
            return round(lightness, 3)
        lightness += step
        if not 0.0 <= lightness <= 1.0:
            raise DesignError(
                "no existe un gris de texto legible sobre esas superficies; "
                "revisa `surface` y `neutral` en design.toml"
            )


# --- The derivation ---------------------------------------------------------


@dataclass(frozen=True)
class _Mode:
    """Lightness and chroma factor of each neutral surface in one mode."""

    background: tuple[float, float]
    foreground: tuple[float, float]
    card: tuple[float, float]
    muted: tuple[float, float]
    accent: tuple[float, float]
    border: tuple[float, float]  # opaque tones; dark mode uses alpha instead
    muted_foreground_start: float


_LIGHT = _Mode(
    background=(1.0, 0.2),
    foreground=(0.145, 1.2),
    card=(1.0, 0.2),
    muted=(0.97, 0.9),
    accent=(0.96, 1.0),
    border=(0.922, 1.0),
    muted_foreground_start=0.556,
)
_CREAM = _Mode(
    background=(0.972, 1.6),
    foreground=(0.18, 1.3),
    card=(0.99, 0.7),
    muted=(0.94, 1.4),
    accent=(0.93, 1.4),
    border=(0.89, 1.4),
    muted_foreground_start=0.5,
)
_DARK = _Mode(
    background=(0.145, 0.8),
    foreground=(0.985, 0.2),
    card=(0.205, 0.8),
    muted=(0.269, 0.9),
    accent=(0.31, 1.0),
    border=(0.985, 0.3),
    muted_foreground_start=0.708,
)

_DESTRUCTIVE_LIGHT = (0.577, 0.245, 27.325)
_DESTRUCTIVE_DARK = (0.704, 0.191, 22.216)


def _build_mode(
    spec: _Mode,
    *,
    dark: bool,
    hue: float,
    unit: float,
    primary: dict[str, str],
    secondary: tuple[str, str] | None,
    secondary_hue: tuple[float, float] | None,
    brand_hue: float,
    brand_chroma: float,
) -> dict[str, str]:
    """Every token of one mode, as the CSS strings that will be written."""

    def neutral(pair: tuple[float, float]) -> Colour:
        return Colour.of(pair[0], unit * pair[1], hue)

    background = neutral(spec.background)
    foreground = neutral(spec.foreground)
    card = neutral(spec.card)
    muted = neutral(spec.muted)
    accent = neutral(spec.accent)
    bg_rgb, card_rgb, muted_rgb = background.rgb, card.rgb, muted.rgb

    if secondary_hue is not None:
        # A brand secondary tints the hover/selected surface too, so the whole
        # interface leans towards it rather than only one button.
        sec_chroma, sec_h = secondary_hue
        accent = Colour.of(accent.lightness, min(sec_chroma * 0.25, 0.04), sec_h)

    muted_fg_l = _solve(
        spec.muted_foreground_start,
        unit * 1.4,
        hue,
        [bg_rgb, card_rgb, muted_rgb, accent.rgb],
        darker=not dark,
    )
    muted_foreground = Colour.of(muted_fg_l, unit * 1.4, hue)

    dl, dc, dh = _DESTRUCTIVE_DARK if dark else _DESTRUCTIVE_LIGHT
    destructive_l = _solve(dl, dc, dh, [bg_rgb, card_rgb], darker=not dark)
    destructive = Colour.of(destructive_l, dc, dh)

    if dark:
        border = Colour.of(spec.border[0], unit * spec.border[1], hue, 0.10)
        field = Colour.of(spec.border[0], unit * spec.border[1], hue, 0.15)
    else:
        border = Colour.of(spec.border[0], unit * spec.border[1], hue)
        field = border

    ring = primary["--ring"]
    tokens: dict[str, str] = {
        "--background": background.css(),
        "--foreground": foreground.css(),
        "--card": card.css(),
        "--card-foreground": foreground.css(),
        "--popover": card.css(),
        "--popover-foreground": foreground.css(),
        "--primary": primary["--primary"],
        "--primary-foreground": primary["--primary-foreground"],
    }
    if secondary is not None:
        tokens["--secondary"], tokens["--secondary-foreground"] = secondary
    else:
        tokens["--secondary"] = muted.css()
        tokens["--secondary-foreground"] = foreground.css()
    tokens.update(
        {
            "--muted": muted.css(),
            "--muted-foreground": muted_foreground.css(),
            "--accent": accent.css(),
            "--accent-foreground": foreground.css(),
            "--destructive": destructive.css(),
            "--border": border.css(),
            "--input": field.css(),
            "--ring": ring,
        }
    )

    # Charts follow the brand hue (Basecoat's are blues, which would clash).
    steps = (
        (0.82, 0.5),
        (0.70, 0.8),
        (0.58, 1.0),
        (0.46, 1.0),
        (0.34, 0.9),
    )
    chart_chroma = min(brand_chroma, 0.15)
    for index, (lightness, factor) in enumerate(steps, start=1):
        tokens[f"--chart-{index}"] = Colour.of(lightness, chart_chroma * factor, brand_hue).css()

    sidebar_l = card.lightness if dark else max(background.lightness - 0.015, 0.0)
    sidebar = Colour.of(sidebar_l, unit * spec.background[1], hue)
    tokens.update(
        {
            "--sidebar": sidebar.css(),
            "--sidebar-foreground": foreground.css(),
            "--sidebar-primary": primary["--primary"],
            "--sidebar-primary-foreground": primary["--primary-foreground"],
            "--sidebar-accent": muted.css(),
            "--sidebar-accent-foreground": foreground.css(),
            "--sidebar-border": border.css(),
            "--sidebar-ring": ring,
        }
    )
    return tokens


def _secondary_group(
    hex_value: str, *, dark: bool, dark_only: bool, dark_background: Rgb
) -> tuple[str, str]:
    """`(--secondary, --secondary-foreground)` for the brand's second colour."""
    group: BrandTokens = brand_tokens(
        hex_value,
        dark_background=dark_background,
        min_dark_lightness=0.0 if dark_only else 0.72,
        min_dark_contrast=3.0 if dark_only else 0.0,
    )
    values = group.dark if dark else group.light
    return values["--primary"], values["--primary-foreground"]


def token_rgb(css_colour: str) -> Rgb:
    """Parse back an `oklch(L C H)` we wrote ourselves."""
    inner = css_colour.removeprefix("oklch(").removesuffix(")").split("/")[0].split()
    return oklch_to_rgb(float(inner[0]), float(inner[1]), float(inner[2]))


def derive_palette(brand: Brand) -> Palette:
    """Every Basecoat colour token for `brand`, light and dark, audited for contrast."""
    hue, unit = neutral_axis(brand)
    dark_only = brand.surface == "dark"
    light_spec = _CREAM if brand.surface == "cream" else _LIGHT

    primary_rgb = parse_hex(brand.primary)
    _, brand_chroma, brand_hue = rgb_to_oklch(primary_rgb)
    secondary_hue: tuple[float, float] | None = None
    if brand.secondary:
        _, sec_chroma, sec_h = rgb_to_oklch(parse_hex(brand.secondary))
        secondary_hue = (sec_chroma, sec_h)

    # The dark background the brand colours must stay visible against.
    dark_bg = Colour.of(_DARK.background[0], unit * _DARK.background[1], hue).rgb
    ref_bg = dark_bg if dark_only else DARK_BACKGROUND
    primary_group = brand_tokens(
        brand.primary,
        dark_background=ref_bg,
        min_dark_lightness=0.0 if dark_only else 0.72,
        min_dark_contrast=3.0 if dark_only else 0.0,
    )

    def build(dark: bool) -> dict[str, str]:
        secondary = None
        if brand.secondary:
            secondary = _secondary_group(
                brand.secondary, dark=dark, dark_only=dark_only, dark_background=ref_bg
            )
        return _build_mode(
            _DARK if dark else light_spec,
            dark=dark,
            hue=hue,
            unit=unit,
            primary=primary_group.dark if dark else primary_group.light,
            secondary=secondary,
            secondary_hue=secondary_hue,
            brand_hue=brand_hue,
            brand_chroma=brand_chroma,
        )

    dark_tokens = build(True)
    light_tokens = dark_tokens if dark_only else build(False)

    pairs: list[ContrastPair] = []
    warnings: list[str] = []
    if not dark_only:
        pairs.extend(_audit("light", light_tokens))
    pairs.extend(_audit("dark", dark_tokens))

    if brand.surface == "cream" and brand.neutral == "cool":
        warnings.append(
            "surface=cream con neutral=cool mezcla temperaturas de gris "
            "(un papel cálido con bordes fríos); usa neutral=warm o surface=light"
        )

    return Palette(
        light=light_tokens,
        dark=dark_tokens,
        dark_only=dark_only,
        pairs=tuple(pairs),
        warnings=tuple(warnings),
        auto=brand.surface == "auto",
    )


# The pairings that decide whether the interface can be read. `required` ones
# stop the build; the rest are reported because the brand colour is a choice.
_REQUIRED: tuple[tuple[str, str], ...] = (
    ("--foreground", "--background"),
    ("--card-foreground", "--card"),
    ("--popover-foreground", "--popover"),
    ("--primary-foreground", "--primary"),
    ("--secondary-foreground", "--secondary"),
    ("--muted-foreground", "--muted"),
    ("--muted-foreground", "--background"),
    ("--accent-foreground", "--accent"),
    ("--destructive", "--background"),
    ("--sidebar-foreground", "--sidebar"),
)
_ADVISORY: tuple[tuple[str, str], ...] = (("--primary", "--background"),)


def _audit(mode: Literal["light", "dark"], tokens: dict[str, str]) -> list[ContrastPair]:
    """Contrast of every pairing, measured on the strings that will be written."""
    pairs: list[ContrastPair] = []
    for required, group in ((True, _REQUIRED), (False, _ADVISORY)):
        for foreground, background in group:
            ratio = contrast_ratio(token_rgb(tokens[foreground]), token_rgb(tokens[background]))
            pairs.append(ContrastPair(mode, foreground, background, ratio, required))
    return pairs


def suggest_primary(hex_value: str) -> str | None:
    """The closest hex to `hex_value` whose button label reads (AA), or None.

    Moves lightness in OKLCH, keeping hue and chroma, so the suggestion is still
    recognisably the same colour.
    """
    lightness, chroma, hue = rgb_to_oklch(parse_hex(hex_value))
    for delta in (i * 0.01 for i in range(0, 60)):
        for signed in (delta, -delta):
            candidate_l = lightness + signed
            if not 0.0 <= candidate_l <= 1.0:
                continue
            candidate = oklch_to_rgb(candidate_l, chroma, hue)
            if foreground_for(candidate)[1] >= TARGET:
                return rgb_to_hex(candidate)
    return None


# --- Rendering --------------------------------------------------------------


def _declarations(values: dict[str, str]) -> str:
    return "\n".join(f"  {name}: {value};" for name, value in values.items())


def render_palette_block(palette: Palette, *, radius: str, source: str = "") -> str:
    """The CSS written between the `kiro:brand` markers of `input.css`."""
    light = dict(palette.light)
    light["--radius"] = radius
    if palette.dark_only:
        # Dark from the first paint, with native controls (scrollbars, date
        # pickers) following. The `dark` class on <html> covers the `dark:`
        # variants; see `app.design_engine.runtime`.
        light["color-scheme"] = "dark"

    # Basecoat maps `--color-background: var(--background)` on :root, and a
    # custom property holding a var() is resolved where it is declared: a
    # descendant inherits the *resolved* value. So `.dark` on <html> works, but
    # `<section class="dark">` inside a light page would keep the light colours.
    # Re-declaring the mapping under `.dark` makes any dark band work, which is
    # how a light site gets a dark hero or footer.
    dark = dict(palette.dark)
    dark.update({f"--color-{name.removeprefix('--')}": f"var({name})" for name in palette.dark})
    if palette.auto:
        # Light unless the system asks for dark, and the browser's own controls
        # (scrollbars, date pickers) follow the same preference.
        light["color-scheme"] = "light dark"

    origin = f" /* {source} */" if source else ""
    return (
        f"{BRAND_BLOCK_START}\n"
        f":root {{{origin}\n{_declarations(light)}\n}}\n\n"
        f".dark {{\n{_declarations(dark)}\n}}\n"
        f"{_auto_dark(palette)}"
        f"{BRAND_BLOCK_END}"
    )


# `dark:` variants of Basecoat follow `html.dark`. With `surface = "auto"` the system
# decides, so the variant is redefined to match either the class (a dark band inside a
# light page) or the media query: no script, no flash of the wrong theme.
_AUTO_VARIANT = """\
@custom-variant dark {
  &:where(.dark, .dark *) {
    @slot;
  }
  @media (prefers-color-scheme: dark) {
    @slot;
  }
}
"""


def _auto_dark(palette: Palette) -> str:
    """The dark tokens under `prefers-color-scheme`, for `surface = "auto"`; else nothing."""
    if not palette.auto:
        return ""
    return (
        "\n@media (prefers-color-scheme: dark) {\n"
        f"  :root {{\n{_indent(_declarations(palette.dark))}\n  }}\n}}\n\n"
        f"{_AUTO_VARIANT}"
    )


def _indent(text: str) -> str:
    return "\n".join(f"  {line}" if line else line for line in text.splitlines())
