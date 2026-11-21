"""The uupm advisor, as one more source for the pipeline.

uupm (nextlevelbuilder's *ui-ux-pro-max*) knows what a product of a given kind
needs: the landing pattern, a style, a palette, a type pairing, the anti-patterns.
`scripts/design.py advise` runs its search (vendored, stdlib-only Python) and hands
the JSON here; this module turns it into a `DesignBrief`, the **base** that
`propose` dresses with whatever inspiration the project adds.

What uupm says is translated with the overlay in `.claude/skills/kiro-design/uupm-kiro/`
(built once by `scripts/vendor_uupm.py`): which of its fonts exist on Fontsource, which
palettes pass AA with Kiro's compiler, which style is nearest to which preset. The
conflicts that remain (its carousel against taste's ban on one, a purple against "no
AI purple") are not decided here: they travel as notes for the review, and
`references/constitution.md` says who wins.

Pure: it reads files you hand it and returns values. Running uupm is the script's job.
"""

from __future__ import annotations

import csv
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.branding import BrandError, parse_hex, rgb_to_oklch
from app.design_engine.brief import BriefColour, BriefFont, DesignBrief
from app.design_engine.contract import DesignError, Fallback, Neutral, Surface
from app.design_engine.presets import PRESETS

#: What uupm pins today; echoed into the provenance line.
UUPM_LABEL = "uupm v2.15.0"

_CATEGORIES: tuple[Fallback, ...] = ("sans", "serif", "mono")
_WEIGHTS = re.compile(r"[?&]family=([^:&]+)(?::wght@([\d;]+))?")


@dataclass(frozen=True)
class FontNote:
    family: str  # the Fontsource family, empty if there is none
    category: Fallback
    weights: tuple[int, ...]


@dataclass(frozen=True)
class PaletteNote:
    primary: str
    aa: str  # ok | fails | invalid
    suggested: str
    purple: bool
    saturated: bool


@dataclass(frozen=True)
class Overlay:
    fonts: Mapping[str, FontNote] = field(default_factory=dict)
    palettes: Mapping[str, PaletteNote] = field(default_factory=dict)
    styles: Mapping[str, str] = field(default_factory=dict)
    skipped_stack_rows: Mapping[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class Advice:
    """What the advisor said, ready for `propose`."""

    brief: DesignBrief
    #: Source font name (case-insensitive) to the Fontsource family that stands for it.
    fonts: Mapping[str, str]
    preset: str


def _read(path: Path) -> list[dict[str, str]]:
    try:
        with path.open(encoding="utf-8", newline="") as handle:
            return list(csv.DictReader(handle))
    except OSError as exc:
        raise DesignError(f"falta {path.name} del solapamiento de uupm: {exc.strerror}") from exc


def load_overlay(directory: Path) -> Overlay:
    """Read the four tables `vendor_uupm` writes."""
    fonts: dict[str, FontNote] = {}
    for row in _read(directory / "fonts.csv"):
        category = row["category"] if row["category"] in _CATEGORIES else "sans"
        weights = tuple(int(w) for w in row["weights"].split() if w.isdigit())
        fonts[row["source_font"].casefold()] = FontNote(
            row["fontsource"],
            category,
            weights,
        )
    palettes = {
        row["product_type"].casefold(): PaletteNote(
            row["primary"],
            row["aa"],
            row["suggested"],
            row["purple"] == "yes",
            row["saturated"] == "yes",
        )
        for row in _read(directory / "palettes.csv")
    }
    styles = {row["style_id"].casefold(): row["preset"] for row in _read(directory / "styles.csv")}
    skips = {row["no"]: row["reason"] for row in _read(directory / "stack-skip.csv")}
    return Overlay(fonts, palettes, styles, skips)


# --- Reading what uupm says ----------------------------------------------------------------


def _mapping(value: object) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _split(text: str, separator: str) -> list[str]:
    return [part.strip() for part in text.split(separator) if part.strip()]


def _background_hints(colours: Mapping[str, Any]) -> tuple[Surface | None, Neutral | None]:
    """The surface and the temperature of the greys, read from uupm's background colours."""
    surface: Surface | None = None
    neutral: Neutral | None = None
    try:
        lightness, chroma, hue = rgb_to_oklch(parse_hex(str(colours["background"])))
    except (KeyError, BrandError):
        return None, None
    if lightness < 0.35:
        surface = "dark"
    elif lightness > 0.9 and chroma >= 0.008 and 50 <= hue <= 110:
        surface = "cream"
    else:
        surface = "light"

    try:
        _, grey_chroma, grey_hue = rgb_to_oklch(parse_hex(str(colours["muted_foreground"])))
    except (KeyError, BrandError):
        return surface, None
    if grey_chroma < 0.012:
        neutral = "pure"
    elif 30 <= grey_hue <= 110:
        neutral = "warm"
    elif 190 <= grey_hue <= 290:
        neutral = "cool"
    else:
        neutral = "tinted"
    return surface, neutral


def _weights_for(role: str, available: tuple[int, ...]) -> tuple[int, ...]:
    """At most two weights, always among those Fontsource has."""
    have = {w for w in available if 100 <= w <= 900}
    if not have:
        return (400,)
    if role == "display":
        heavy = sorted(w for w in have if w in (600, 700))
        chosen = heavy[-2:] or [max(have)]
        return tuple(chosen)
    bold = next((w for w in (600, 700, 500) if w in have), None)
    return (400, bold) if 400 in have and bold else ((400,) if 400 in have else (min(have),))


def _requested_weights(url: str, family: str) -> tuple[int, ...]:
    for name, weights in _WEIGHTS.findall(url):
        if name.replace("+", " ") == family and weights:
            return tuple(int(w) for w in weights.split(";") if w.isdigit())
    return ()


def _fonts(
    typography: Mapping[str, Any], overlay: Overlay
) -> tuple[list[BriefFont], dict[str, str]]:
    url = str(typography.get("google_fonts_url", ""))
    briefs: list[BriefFont] = []
    table: dict[str, str] = {}
    for key, role in (("heading", "display"), ("body", "body")):
        name = str(typography.get(key, "")).strip()
        if not name:
            continue
        note = overlay.fonts.get(name.casefold())
        category: Fallback = note.category if note else "sans"
        available = note.weights if note and note.weights else _requested_weights(url, name)
        briefs.append(
            BriefFont(
                name=name,
                role=role,
                category=category,
                weights=_weights_for(role, available),
            )
        )
        if note and note.family:
            table[name.casefold()] = note.family
    return briefs, table


def brief_from_design_system(
    data: Mapping[str, Any],
    overlay: Overlay,
    *,
    dials: Mapping[str, int] | None = None,
) -> Advice:
    """Turn `search.py --design-system --json` into the base brief.

    `dials` are the project's own (`variance`, `motion`, `density`, from DESIGN.md);
    without them the nearest preset's are used.
    """
    system = data.get("design_system")
    if not isinstance(system, Mapping):
        raise DesignError("la respuesta de uupm no trae un `design_system`")
    category = str(system.get("category", "")).strip() or "producto"
    style = _mapping(system.get("style"))
    colours = _mapping(system.get("colors"))
    typography = _mapping(system.get("typography"))
    pattern = _mapping(system.get("pattern"))
    dials = dials or {}

    style_id = str(style.get("id", "")).casefold()
    preset_name = overlay.styles.get(style_id, "")
    preset = PRESETS.get(preset_name) if preset_name else None

    notes: list[str] = []
    ux: list[str] = []
    if pattern:
        sections = str(pattern.get("sections", ""))
        ux.append(
            f"Patrón de landing para {category}: {pattern.get('name', '')} ({sections}). "
            "uupm decide qué secciones y en qué orden; taste decide cómo se compone cada una."
        )
        conversion = str(pattern.get("conversion", ""))
        if conversion:
            ux.append(f"Conversión: {conversion}")
        if re.search(r"carousel|carrusel", f"{sections} {conversion}", re.IGNORECASE):
            ux.append(
                "uupm propone un carrusel de testimonios y taste lo prohíbe (P3): "
                "muestra dos o tres citas con nombre y contexto, sin carrusel."
            )
    accessibility = str(style.get("accessibility", ""))
    if accessibility:
        ux.append(f"Accesibilidad del estilo ({style.get('name', '')}): {accessibility}")
    for constraint in system.get("constraints", []) or []:
        ux.append(f"Requisito del producto: {constraint}")

    palette_note = overlay.palettes.get(category.casefold())
    if palette_note is not None:
        if palette_note.purple:
            notes.append(
                "La paleta de uupm es morada: se conserva solo si es el tono de la marca "
                "(saturación bajo el 80 % y sin brillo)."
            )
        if palette_note.saturated:
            notes.append("El primario de uupm tiene una saturación por encima del 80 %.")
    ux.extend(f"taste: {note}" for note in notes)

    brief_colours: list[BriefColour] = []
    for role, key, weight in (
        ("primary", "primary", 0.6),
        ("secondary", "secondary", 0.2),
        ("accent", "accent", 0.1),
    ):
        value = colours.get(key)
        if value:
            brief_colours.append(BriefColour(hex=str(value), role=role, weight=weight))

    surface, neutral = _background_hints(colours)
    fonts, table = _fonts(typography, overlay)

    anti = [item for item in _split(str(system.get("anti_patterns", "")), "+") if item]
    keywords = _split(str(style.get("keywords", "")), ",")[:8]
    style_name = str(style.get("name", ""))
    where = f"{UUPM_LABEL}: {category}"
    if style_name:
        where += f" / {style_name}"
        if preset_name:
            where += f" (base: {preset_name})"

    contract = preset.contract if preset else None
    brief = DesignBrief(
        source="advisor",
        provenance=where,
        title=category,
        colours=tuple(brief_colours),
        fonts=tuple(fonts),
        radius=contract.brand.radius if contract else None,
        neutral=neutral,
        surface=surface,
        theme=contract.basecoat.theme if contract else None,
        header=contract.structure.header if contract else None,
        density=dials.get("density", preset.density if preset else None),
        motion=dials.get("motion", preset.motion if preset else None),
        keywords=tuple(keywords),
        ux_notes=tuple(ux),
        anti_patterns=tuple(anti),
    )
    return Advice(brief=brief, fonts=table, preset=preset_name)
