"""skillui's output, as a brief.

[skillui](https://github.com/amaancoderx/npxskillui) is a Node tool, so it stays outside
this repository (ADR-0005): a person installs it if they want it, and
`scripts/reference.py skillui <url>` runs it into `.design/reference/`. What it writes
(`tokens/colors.json`, `tokens/typography.json`, `tokens/spacing.json` and a `DESIGN.md`)
is read here. The schemas are those of skillui 1.3.x; it does not publish them, so this
reader takes what is there and tolerates what is not.

Pure: it receives the parsed JSON, not paths. As everywhere, only the language is
read: colours, family names, a rhythm; never its screenshots, its fonts or its code.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

from app.branding import BrandError
from app.design_engine.brief import BriefColour, BriefFont, DesignBrief, FontRole
from app.design_engine.cssread import category_of, clean_family, find_colours, radius_from, role_of
from app.design_engine.external_md import brief_from_markdown

_SIZE = re.compile(r"(\d+(?:\.\d+)?)\s*(px|rem|em)?")


def _mapping(value: object) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _px(value: object) -> float:
    match = _SIZE.search(str(value))
    if not match:
        return 0.0
    number = float(match.group(1))
    return number * 16 if match.group(2) in ("rem", "em") else number


def _colours(colors: Mapping[str, Any]) -> list[BriefColour]:
    entries: list[tuple[str, str]] = []
    for group in ("core", "status", "extended"):
        for key, entry in _mapping(colors.get(group)).items():
            data = _mapping(entry)
            found = find_colours(str(data.get("value", "")))
            if found:
                label = f"{key} {data.get('role', '')} {data.get('name', '')}"
                entries.append((found[0], label if group == "core" else "other"))

    result: list[BriefColour] = []
    seen: set[str] = set()
    for index, (hex_value, label) in enumerate(entries):
        if hex_value in seen:
            continue
        seen.add(hex_value)
        # Earlier entries are the core palette: they weigh more than the long tail.
        weight = round(max(0.05, 1.0 - index * 0.05), 2)
        result.append(BriefColour(hex=hex_value, role=role_of(label), weight=weight))
    return result[:24]


def _fonts(typography: Mapping[str, Any]) -> list[BriefFont]:
    scale = _mapping(typography.get("scale"))
    by_role: dict[FontRole, tuple[float, str, str, int]] = {}
    for label, entry in scale.items():
        data = _mapping(entry)
        raw = str(data.get("fontFamily", ""))
        family = clean_family(raw)
        if not family:
            continue
        size = _px(data.get("fontSize"))
        lowered = str(label).lower()
        role: FontRole = (
            "mono"
            if re.search(r"mono|code", lowered) or category_of(family) == "mono"
            else "display"
            if re.search(r"display|heading|headline|title|hero|\bh[1-3]\b", lowered)
            else "body"
        )
        weight = int(_px(data.get("fontWeight"))) or 400
        best = by_role.get(role)
        # The biggest size speaks for the display face; for the body, the first one wins.
        if best is None or (role == "display" and size > best[0]):
            by_role[role] = (size, family, raw, weight)

    if not by_role:
        families = [f for raw in typography.get("families", []) if (f := clean_family(str(raw)))]
        if families:
            by_role["body"] = (0.0, families[0], families[0], 400)

    fonts: list[BriefFont] = []
    for role in ("display", "body", "mono"):
        if role not in by_role:
            continue
        _, family, _, weight = by_role[role]
        category = "mono" if role == "mono" else category_of(family, None)
        # A light or regular display face stays at one weight; a bold one gets two.
        weights = ((400,) if weight <= 500 else (600, 700)) if role == "display" else (400, 600)
        fonts.append(BriefFont(name=family, role=role, category=category, weights=weights))
    if len(fonts) >= 2 and fonts[0].role == "display" and fonts[0].name == fonts[1].name:
        fonts = fonts[1:]
    return fonts


def _density(spacing: Mapping[str, Any]) -> int | None:
    base = _px(_mapping(spacing.get("base")).get("value")) or _px(spacing.get("unit"))
    if base <= 0:
        return None
    if base <= 4:
        return 7
    if base <= 6:
        return 5
    return 4 if base <= 8 else 3


def brief_from_skillui(
    *,
    colors: Mapping[str, Any] | None = None,
    typography: Mapping[str, Any] | None = None,
    spacing: Mapping[str, Any] | None = None,
    design_md: str | None = None,
    provenance: str,
) -> DesignBrief:
    """Join skillui's token files (and its `DESIGN.md`, if any) into one brief."""
    colors, typography, spacing = colors or {}, typography or {}, spacing or {}
    palette = _colours(colors)
    fonts = _fonts(typography)

    from_md: DesignBrief | None = None
    if design_md:
        try:
            from_md = brief_from_markdown(design_md, source="reference", provenance=provenance)
        except BrandError:
            from_md = None

    if not palette and not fonts and from_md is None:
        raise BrandError(
            "no encuentro colores ni fuentes en la salida de skillui "
            "(¿falta tokens/colors.json o tokens/typography.json?)"
        )
    if not palette and from_md is not None:
        palette = list(from_md.colours)
    if not fonts and from_md is not None:
        fonts = list(from_md.fonts)

    meta = _mapping(colors.get("meta"))
    dark = str(meta.get("theme", "")).lower() == "dark"
    radius = radius_from(str(v) for v in _mapping(spacing.get("radius")).values()) or (
        from_md.radius if from_md else None
    )
    return DesignBrief(
        source="reference",
        provenance=provenance,
        title=(from_md.title if from_md else "") or "Referencia",
        colours=tuple(palette),
        fonts=tuple(fonts),
        radius=radius,
        surface="dark" if dark else (from_md.surface if from_md else None),
        density=_density(spacing) or (from_md.density if from_md else None),
        motion=from_md.motion if from_md else None,
        ux_notes=from_md.ux_notes if from_md else (),
        anti_patterns=from_md.anti_patterns if from_md else (),
    )
