"""Brand assets: the project's logo and its colour tokens.

Two jobs, both pure so they are easy to test:

1. **Logo.** `find_logo` tells templates whether the project has one, and
   `validate_logo` decides whether a file is safe and usable before
   `scripts/brand.py` copies it into `app/static/brand/`.
2. **Colour.** `brand_tokens` turns a brand hex into the Basecoat CSS variables
   (oklch), picking a readable foreground by WCAG contrast. Colours are derived,
   not eyeballed, so a pale brand colour cannot end up with white text on it.

Nothing here touches the database or the request.
"""

from __future__ import annotations

import math
import re
import struct
from dataclasses import dataclass
from pathlib import Path

STATIC_DIR = Path(__file__).parent / "static"
BRAND_DIR = STATIC_DIR / "brand"

# SVG first: it scales, and it is the format `DESIGN.md` recommends.
LOGO_NAMES = ("logo.svg", "logo.png")
MAX_LOGO_BYTES = 1_000_000

_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


class BrandError(ValueError):
    """A logo or colour that cannot be used. The message is meant for the user."""


# --- Logo -------------------------------------------------------------------


def find_logo(brand_dir: Path = BRAND_DIR) -> Path | None:
    """The project's logo file, or None if it has not been set."""
    for name in LOGO_NAMES:
        candidate = brand_dir / name
        if candidate.is_file():
            return candidate
    return None


def logo_path_relative_to_static(logo: Path) -> str:
    """`brand/logo.svg`, the form `asset()` expects."""
    return f"brand/{logo.name}"


# `on*=` handlers, script tags, remote references and entity tricks. A logo is
# decoration: there is no legitimate reason for any of these, and an SVG opened
# directly (not through <img>) would run them.
_SVG_FORBIDDEN = re.compile(
    r"<\s*script|<\s*foreignObject|<!\s*(?:ENTITY|DOCTYPE)|javascript:"
    r"|\bon[a-z]+\s*=|(?:xlink:)?href\s*=\s*[\"']\s*(?!#|data:image/)",
    re.IGNORECASE,
)
_SVG_VIEWBOX = re.compile(
    r"viewBox\s*=\s*[\"']\s*[-\d.]+[ ,]+[-\d.]+[ ,]+([\d.]+)[ ,]+([\d.]+)\s*[\"']",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class LogoCheck:
    """Result of validating a logo. `extension` says where it should be saved."""

    extension: str  # ".svg" or ".png"
    warning: str | None = None


def validate_logo(data: bytes) -> LogoCheck:
    """Accept an SVG or a square PNG; raise `BrandError` for anything else.

    The format is sniffed from the bytes, not trusted from the file name or a
    URL: a `.png` that is really HTML must not be copied into `static/`.
    """
    if not data:
        raise BrandError("el archivo está vacío")
    if len(data) > MAX_LOGO_BYTES:
        raise BrandError(
            f"el logo pesa {len(data) // 1000} KB; el máximo son {MAX_LOGO_BYTES // 1000} KB"
        )
    if data.startswith(_PNG_SIGNATURE):
        return _validate_png(data)
    return _validate_svg(data)


def _validate_png(data: bytes) -> LogoCheck:
    # IHDR is always the first chunk: 8 signature + 4 length + 4 "IHDR" + 4 width + 4 height.
    if len(data) < 24 or data[12:16] != b"IHDR":
        raise BrandError("el PNG está dañado")
    width, height = struct.unpack(">II", data[16:24])
    if width != height:
        raise BrandError(
            f"el PNG mide {width}x{height}; debe ser cuadrado (1:1). Recórtalo o expórtalo como SVG"
        )
    warning = None
    if width < 128:
        warning = f"el PNG es de {width}px; con menos de 128px se verá borroso en pantallas HiDPI"
    return LogoCheck(".png", warning)


def _validate_svg(data: bytes) -> LogoCheck:
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise BrandError("no es un PNG ni un SVG (no es texto UTF-8)") from exc
    if not re.search(r"<\s*svg[\s>]", text, re.IGNORECASE):
        raise BrandError("no es un PNG ni un SVG válido")
    if _SVG_FORBIDDEN.search(text):
        raise BrandError(
            "el SVG contiene scripts, manejadores on*, referencias externas o entidades; "
            "expórtalo de nuevo sin ellos"
        )
    warning = None
    match = _SVG_VIEWBOX.search(text)
    if match:
        width, height = float(match.group(1)), float(match.group(2))
        if height and not math.isclose(width / height, 1.0, rel_tol=0.05):
            warning = (
                f"el SVG no es cuadrado (viewBox {width:g}x{height:g}); "
                "se mostrará completo pero como logotipo horizontal, no como icono 1:1"
            )
    return LogoCheck(".svg", warning)


# --- Colour -----------------------------------------------------------------

_HEX = re.compile(r"^#?([0-9a-fA-F]{6}|[0-9a-fA-F]{3})$")


def parse_hex(value: str) -> tuple[float, float, float]:
    """`#0F766E` or `0f6` to sRGB floats in 0..1."""
    match = _HEX.match(value.strip())
    if not match:
        raise BrandError(f"'{value}' no es un color hex válido (ej. #0F766E)")
    digits = match.group(1)
    if len(digits) == 3:
        digits = "".join(ch * 2 for ch in digits)
    r, g, b = (int(digits[i : i + 2], 16) / 255 for i in (0, 2, 4))
    return r, g, b


def _to_linear(channel: float) -> float:
    return channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4


def relative_luminance(rgb: tuple[float, float, float]) -> float:
    r, g, b = (_to_linear(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_ratio(a: tuple[float, float, float], b: tuple[float, float, float]) -> float:
    """WCAG contrast ratio between two sRGB colours (1..21)."""
    la, lb = relative_luminance(a), relative_luminance(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def rgb_to_oklch(rgb: tuple[float, float, float]) -> tuple[float, float, float]:
    """sRGB (0..1) to OKLCH (L 0..1, C, H degrees). Björn Ottosson's matrices."""
    r, g, b = (_to_linear(c) for c in rgb)
    l_ = (0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b) ** (1 / 3)
    m_ = (0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b) ** (1 / 3)
    s_ = (0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b) ** (1 / 3)
    lightness = 0.2104542553 * l_ + 0.7936177850 * m_ - 0.0040720468 * s_
    a = 1.9779984951 * l_ - 2.4285922050 * m_ + 0.4505937099 * s_
    b2 = 0.0259040371 * l_ + 0.7827717662 * m_ - 0.8086757660 * s_
    chroma = math.hypot(a, b2)
    hue = math.degrees(math.atan2(b2, a)) % 360 if chroma > 1e-4 else 0.0
    return lightness, chroma, hue


def oklch_to_rgb(lightness: float, chroma: float, hue: float) -> tuple[float, float, float]:
    """OKLCH back to clamped sRGB (0..1), for contrast checks on derived colours."""
    a = chroma * math.cos(math.radians(hue))
    b = chroma * math.sin(math.radians(hue))
    l_ = (lightness + 0.3963377774 * a + 0.2158037573 * b) ** 3
    m_ = (lightness - 0.1055613458 * a - 0.0638541728 * b) ** 3
    s_ = (lightness - 0.0894841775 * a - 1.2914855480 * b) ** 3
    lin = (
        4.0767416621 * l_ - 3.3077115913 * m_ + 0.2309699292 * s_,
        -1.2684380046 * l_ + 2.6097574011 * m_ - 0.3413193965 * s_,
        -0.0041960863 * l_ - 0.7034186147 * m_ + 1.7076147010 * s_,
    )

    def encode(c: float) -> float:
        c = min(max(c, 0.0), 1.0)
        return 12.92 * c if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055

    return encode(lin[0]), encode(lin[1]), encode(lin[2])


def format_oklch(lightness: float, chroma: float, hue: float, alpha: float | None = None) -> str:
    """`oklch(L C H)` as CSS, with an optional `/ N%` alpha."""
    suffix = f" / {alpha * 100:g}%" if alpha is not None else ""
    return f"oklch({lightness:.3f} {chroma:.3f} {hue:.1f}{suffix})"


# The two foregrounds Basecoat itself uses on a filled surface. The contrast we
# report is measured against these exact colours, not against pure white/black:
# `oklch(0.985 0 0)` is a touch darker than #fff, and that difference is what
# separates a 4.6:1 button from a 4.4:1 one.
FOREGROUND_ON_DARK = (0.985, 0.0, 0.0)  # light text, for dark fills
FOREGROUND_ON_LIGHT = (0.145, 0.0, 0.0)  # ink, for light fills
_LIGHT_TEXT = oklch_to_rgb(*FOREGROUND_ON_DARK)
_INK = oklch_to_rgb(*FOREGROUND_ON_LIGHT)
# Basecoat's own dark background, so the contrast we report is the real one.
DARK_BACKGROUND = oklch_to_rgb(0.145, 0.0, 0.0)


@dataclass(frozen=True)
class BrandTokens:
    """The Basecoat variables derived from one brand colour."""

    light: dict[str, str]
    dark: dict[str, str]
    contrast_light: float  # primary-foreground on primary
    contrast_dark: float


def foreground_for(rgb: tuple[float, float, float]) -> tuple[str, float]:
    """Light text or ink, whichever reads better on `rgb`, with the resulting ratio."""
    on_light, on_ink = contrast_ratio(rgb, _LIGHT_TEXT), contrast_ratio(rgb, _INK)
    if on_light >= on_ink:
        return format_oklch(*FOREGROUND_ON_DARK), on_light
    return format_oklch(*FOREGROUND_ON_LIGHT), on_ink


def brand_tokens(
    primary_hex: str,
    *,
    dark_background: tuple[float, float, float] = DARK_BACKGROUND,
    min_dark_lightness: float = 0.72,
    min_dark_contrast: float = 0.0,
) -> BrandTokens:
    """Derive light and dark `--primary`, `--primary-foreground` and `--ring`.

    Light mode keeps the brand colour exactly as given. Dark mode keeps hue and
    chroma but raises lightness to at least `min_dark_lightness` (0.72 by
    default), because a mid-dark brand colour that works on white sinks into a
    near-black background.

    A project whose surface *is* dark passes `min_dark_lightness=0` and a
    `min_dark_contrast`: the brand colour is then lifted only as far as it needs
    to be visible against `dark_background`, instead of being repainted pastel.
    """
    rgb = parse_hex(primary_hex)
    lightness, chroma, hue = rgb_to_oklch(rgb)
    fg_light, contrast_light = foreground_for(rgb)

    dark_lightness = max(lightness, min_dark_lightness)
    dark_rgb = oklch_to_rgb(dark_lightness, chroma, hue)
    while contrast_ratio(dark_rgb, dark_background) < min_dark_contrast and dark_lightness < 0.99:
        dark_lightness = min(dark_lightness + 0.01, 0.99)
        dark_rgb = oklch_to_rgb(dark_lightness, chroma, hue)
    fg_dark, contrast_dark = foreground_for(dark_rgb)

    return BrandTokens(
        light={
            "--primary": format_oklch(lightness, chroma, hue),
            "--primary-foreground": fg_light,
            "--ring": format_oklch(min(max(lightness, 0.55), 0.75), chroma * 0.8, hue),
        },
        dark={
            "--primary": format_oklch(dark_lightness, chroma, hue),
            "--primary-foreground": fg_dark,
            "--ring": format_oklch(dark_lightness, chroma * 0.8, hue),
        },
        contrast_light=contrast_light,
        contrast_dark=min(contrast_dark, contrast_ratio(dark_rgb, dark_background)),
    )


BRAND_BLOCK_START = "/* kiro:brand:start — generado por `make design build`; no editar a mano */"
BRAND_BLOCK_END = "/* kiro:brand:end */"


def render_brand_block(
    tokens: BrandTokens, *, radius: str | None = None, primary_hex: str = ""
) -> str:
    """The CSS block `scripts/brand.py` writes into `input.css`."""

    def declarations(values: dict[str, str]) -> str:
        return "\n".join(f"  {name}: {value};" for name, value in values.items())

    light = dict(tokens.light)
    if radius:
        light["--radius"] = radius
    source = f" /* origen: {primary_hex.upper()} */" if primary_hex else ""
    return (
        f"{BRAND_BLOCK_START}\n"
        f":root {{{source}\n{declarations(light)}\n}}\n\n"
        f".dark {{\n{declarations(tokens.dark)}\n}}\n"
        f"{BRAND_BLOCK_END}"
    )


def apply_brand_block(css: str, block: str) -> str:
    """Insert or replace the brand block in `input.css`, idempotently.

    The block goes right after the "Personalización del proyecto" header comment
    so it lands after Basecoat's import and wins by order. Running it twice
    replaces, never duplicates.
    """
    pattern = re.compile(
        re.escape(BRAND_BLOCK_START.split(" — ")[0]) + r".*?" + re.escape(BRAND_BLOCK_END),
        re.DOTALL,
    )
    if pattern.search(css):
        return pattern.sub(lambda _: block, css, count=1)
    anchor = '@source "../../../app/**/*.py";'
    if anchor not in css:
        raise BrandError("no encuentro dónde insertar el bloque en input.css (¿lo has reescrito?)")
    return css.replace(anchor, f"{anchor}\n\n{block}", 1)
