"""Reading visual language out of CSS and prose, shared by every importer.

A reference site, a skillui folder and a pasted Refero or Stitch `DESIGN.md` all say
the same few things in different formats: some colours (and which one the brand
uses), a few font families, a corner radius, how much it moves. This module is the
small, boring part they share: turning `rgb(0 102 204)` or `"Inter", sans-serif`
into the values a `DesignBrief` holds.

Only values are read. Nothing here fetches a file, a font or an image: the importers
take the *language* of a reference (see `references/constitution.md` and ADR-0021), not
its assets.
"""

from __future__ import annotations

import colorsys
import re
from collections import Counter
from collections.abc import Iterable

from app.design_engine.brief import ColourRole, css_length_to_rem, format_rem
from app.design_engine.contract import Fallback

_HEX = re.compile(r"#(?:[0-9a-fA-F]{8}|[0-9a-fA-F]{6}|[0-9a-fA-F]{3})(?![0-9a-zA-Z_-])")
_RGB = re.compile(
    r"rgba?\(\s*([\d.]+%?)[\s,]+([\d.]+%?)[\s,]+([\d.]+%?)(?:[\s,/]+[\d.]+%?)?\s*\)", re.IGNORECASE
)
_HSL = re.compile(
    r"hsla?\(\s*([\d.]+)(?:deg)?[\s,]+([\d.]+)%[\s,]+([\d.]+)%(?:[\s,/]+[\d.]+%?)?\s*\)",
    re.IGNORECASE,
)

#: Families that are not a choice: keywords of CSS, and the generic stacks.
GENERIC_FAMILIES = frozenset(
    {
        "inherit", "initial", "unset", "revert", "serif", "sans-serif", "monospace", "cursive",
        "fantasy", "system-ui", "ui-sans-serif", "ui-serif", "ui-monospace", "ui-rounded",
        "emoji", "math", "fangsong", "-apple-system", "blinkmacsystemfont", "arial",
        "helvetica", "helvetica neue", "segoe ui", "roboto", "times new roman", "times",
        "courier new", "courier", "georgia", "verdana", "tahoma", "trebuchet ms", "menlo",
        "monaco", "consolas", "sfmono-regular", "sf pro", "sf pro text", "sf pro display",
    }
)  # fmt: skip
_FAMILY_SUFFIX = re.compile(r"\s+(?:variable|var|vf|text|display)$", re.IGNORECASE)
_NAME_OK = re.compile(r"^[A-Za-z][A-Za-z0-9 ]{0,59}$")

_SERIFS = re.compile(
    r"georgia|garamond|playfair|merriweather|lora|baskerville|didot|bodoni|caslon|fraunces|"
    r"newsreader|crimson|cormorant|libre|source serif|noto serif|dm serif|young serif|gloock|"
    r"instrument serif|spectral|literata|charter|palatino|(?<!sans )serif",
    re.IGNORECASE,
)
_MONOS = re.compile(r"mono|code|courier|consolas|menlo|fira code|plex mono", re.IGNORECASE)


def _clamp(value: float) -> int:
    return max(0, min(255, int(value + 0.5)))


def _channel(raw: str) -> int:
    return _clamp(float(raw[:-1]) * 2.55 if raw.endswith("%") else float(raw))


def find_colours(text: str) -> list[str]:
    """Every colour written in `text` as `#RRGGBB`, in order of appearance.

    Reads `#rgb`, `#rrggbb`, `#rrggbbaa` (the alpha is dropped), `rgb()`/`rgba()` and
    `hsl()`/`hsla()`. Anything it cannot read is skipped, never guessed.
    """
    found: list[tuple[int, str]] = []
    for match in _HEX.finditer(text):
        digits = match.group(0)[1:]
        if len(digits) == 3:
            digits = "".join(ch * 2 for ch in digits)
        found.append((match.start(), f"#{digits[:6].upper()}"))
    for match in _RGB.finditer(text):
        r, g, b = (_channel(match.group(i)) for i in (1, 2, 3))
        found.append((match.start(), f"#{r:02X}{g:02X}{b:02X}"))
    for match in _HSL.finditer(text):
        h, s, lightness = (
            float(match.group(1)) / 360,
            float(match.group(2)) / 100,
            float(match.group(3)) / 100,
        )
        r_, g_, b_ = colorsys.hls_to_rgb(h % 1.0, lightness, s)
        found.append(
            (match.start(), f"#{_clamp(r_ * 255):02X}{_clamp(g_ * 255):02X}{_clamp(b_ * 255):02X}")
        )
    return [colour for _, colour in sorted(found)]


_BRAND_WORDS = re.compile(r"primary|brand|accent|cta|action|button|link|highlight|tint")
_TEXT_WORDS = re.compile(r"\btext\b|foreground|\bink\b|\bcopy\b|heading|\bbody\b")


def role_of(label: str) -> ColourRole:
    """What a colour is for, from the words around it ("Primary / CTA", "Page background").

    Order matters: "text-primary" is the primary *text* colour, not the brand's, and a
    button's label colour ("Primary button text") is neither the brand nor the text
    colour of the page.
    """
    lowered = label.lower()
    if _TEXT_WORDS.search(lowered):
        return "other" if re.search(r"button|cta|link", lowered) else "text"
    if re.search(r"secondary|support|second", lowered):
        return "secondary"
    if _BRAND_WORDS.search(lowered):
        return "primary"
    if re.search(r"background|canvas|\bpage\b|\bbg\b", lowered):
        return "background"
    if re.search(r"surface|card|panel|elevated|container", lowered):
        return "surface"
    return "other"


def clean_family(raw: str) -> str | None:
    """The first real family of a `font-family` value, or None if there is none.

    `"Inter Variable", system-ui, sans-serif` is Inter; `system-ui, sans-serif` and
    `Arial` are not a choice a reference made. A proprietary face (Helvetica Neue, SF
    Pro) is not copied: it has no Fontsource file and the importer maps it by category.
    """
    for item in raw.split(","):
        name = item.strip().strip("\"'").strip()
        name = _FAMILY_SUFFIX.sub("", name).strip()
        if not name or name.lower() in GENERIC_FAMILIES or name.startswith("var("):
            continue
        name = name.replace("-", " ")
        name = " ".join(name.split())
        if _NAME_OK.match(name):
            return name
        return None
    return None


def generic_of(raw: str) -> Fallback | None:
    """The generic family a `font-family` value ends with (`serif`, `monospace`)."""
    lowered = raw.lower()
    if re.search(r"\bmonospace\b|ui-monospace", lowered):
        return "mono"
    if re.search(r"(?<!sans-)\bserif\b|ui-serif", lowered):
        return "serif"
    return None


def category_of(name: str, generic: Fallback | None = None) -> Fallback | None:
    """serif, mono or sans (None when nothing says): by the generic family, then by name."""
    if generic is not None:
        return generic
    if _MONOS.search(name):
        return "mono"
    if _SERIFS.search(name):
        return "serif"
    return None


def radius_from(values: Iterable[str]) -> str | None:
    """The corner radius a reference uses most, as a CSS length in rem.

    Pills (`9999px`, `50%`) and zeros are not the typical radius; they are kept out of
    the count unless that is all there is, in which case a flat design is `0`.
    """
    rems: Counter[float] = Counter()
    flat = 0
    for raw in values:
        value = raw.strip().lower()
        if value.endswith("%") or value in {"inherit", "initial", "unset"}:
            continue
        rem = css_length_to_rem(value.split()[0]) if value.split() else None
        if rem is None:
            continue
        if rem == 0:
            flat += 1
        elif rem < 5:  # 5 rem = 80 px: above that it is a pill, not a radius
            rems[round(rem, 3)] += 1
    if rems:
        return format_rem(rems.most_common(1)[0][0])
    return "0rem" if flat else None
