"""Reading a `DESIGN.md` written by someone else.

Three sources write the same kind of document: **Refero Styles** (its "Copy .md"
export), **skillui** (its `DESIGN.md`, in the Google Stitch nine-section format) and
the collections that follow that format (awesome-design-md). They have tables of
colours, a type scale, spacing and radii, components, and Do and Don't lists. One tolerant
reader covers all three, so a fourth source is not a fourth parser.

It reads **language, not assets**: colours, family names, a radius, how much it moves,
what to avoid. It never follows a link, downloads a font or an image, or copies a
component's code. Whatever it cannot read is left out and reported by `propose` as
something for a person to decide, never guessed.

The format is not versioned by its authors, so the reader is deliberately forgiving: it
looks for the *shape* (a table under a heading about colour, with a hex in a row) and not
for exact titles.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field

from app.branding import BrandError, parse_hex, rgb_to_oklch
from app.design_engine.brief import (
    BriefColour,
    BriefFont,
    ColourRole,
    DesignBrief,
    FontRole,
    Source,
)
from app.design_engine.cssread import (
    category_of,
    clean_family,
    find_colours,
    generic_of,
    radius_from,
    role_of,
)

MAX_BYTES = 600_000
MAX_COLOURS = 24

_HEADING = re.compile(r"^(#{1,4})\s+(.*?)\s*#*\s*$")
_BULLET = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+(.*)$")
_TITLE_NOISE = re.compile(
    r"\s*[—\u2013:|-]\s*(style reference|design system|design\.md|design guide|style guide).*$",
    re.IGNORECASE,
)
_WEIGHT_WORDS = {
    "thin": 100, "extralight": 200, "light": 300, "regular": 400, "normal": 400,
    "medium": 500, "semibold": 600, "semi-bold": 600, "bold": 700, "extrabold": 800,
    "black": 900,
}  # fmt: skip
_ROLE_FONT: tuple[tuple[str, FontRole], ...] = (
    (r"mono|code|tabular", "mono"),
    (r"display|heading|headline|title|hero|\bh[1-3]\b", "display"),
    (r"body|text|paragraph|copy|ui|label|caption|button", "body"),
)
_FONT_LINE = re.compile(
    r"(?:\*\*|`)?(display|heading|headline|title|body|text|mono|code)(?:\*\*|`)?"
    r"\s*(?:font|face|family|typeface)?\s*[:\-\u2013\u2014]\s*(?:\*\*|`)?\s*"
    r"([A-Z][A-Za-z0-9 ]{1,40})",
    re.IGNORECASE,
)
_FONT_DECL = re.compile(r"font-family\s*:\s*([^;\n}]+)", re.IGNORECASE)
_RADIUS_DECL = re.compile(r"border-radius\s*:\s*([^;\n}]+)", re.IGNORECASE)
_LENGTH = re.compile(r"\b(\d+(?:\.\d+)?)\s*(px|rem)\b")


@dataclass
class _Section:
    heading: str
    level: int
    lines: list[str] = field(default_factory=list)

    @property
    def key(self) -> str:
        return self.heading.lower()


def _sections(text: str) -> list[_Section]:
    result = [_Section("", 0)]
    fence = False
    for line in text.splitlines():
        if line.strip().startswith("```"):
            fence = not fence
        match = None if fence else _HEADING.match(line)
        if match:
            result.append(_Section(match.group(2).strip(), len(match.group(1))))
        else:
            result[-1].lines.append(line)
    return result


def _cells(line: str) -> list[str] | None:
    stripped = line.strip()
    if not stripped.startswith("|"):
        return None
    cells = [c.strip().strip("`*") for c in stripped.strip("|").split("|")]
    if all(re.fullmatch(r":?-{2,}:?", c) for c in cells if c):
        return None  # the separator row
    return cells


def _tables(section: _Section) -> list[tuple[list[str], list[list[str]]]]:
    """`(header, rows)` for each table in a section."""
    tables: list[tuple[list[str], list[list[str]]]] = []
    current: list[list[str]] = []
    for line in [*section.lines, ""]:
        cells = _cells(line)
        if cells is not None:
            current.append(cells)
        elif line.strip().startswith("|"):
            continue
        elif current:
            tables.append((current[0], current[1:]))
            current = []
    return tables


def _title(text: str) -> str:
    for line in text.splitlines():
        match = _HEADING.match(line)
        if match and len(match.group(1)) == 1:
            return _TITLE_NOISE.sub("", match.group(2)).strip()[:80]
    return ""


def _is(section: _Section, pattern: str) -> bool:
    return re.search(pattern, section.key) is not None


# --- Colours ------------


def _colours(text: str, sections: list[_Section]) -> list[BriefColour]:
    uses = Counter(find_colours(text))
    if not uses:
        return []
    most = max(uses.values())

    chosen: dict[str, ColourRole] = {}

    def keep(hex_value: str, role: ColourRole) -> None:
        if hex_value not in chosen or (chosen[hex_value] == "other" and role != "other"):
            chosen[hex_value] = role

    wanted = [s for s in sections if _is(s, r"colou?r|palette|paleta")]
    for section in wanted:
        for _header, rows in _tables(section):
            for row in rows:
                label = " ".join(row)
                for hex_value in find_colours(label):
                    # The name and role cells, not the value: "Primary / CTA", "Page background".
                    keep(hex_value, role_of(" ".join(c for c in row if not find_colours(c))))
        for line in section.lines:
            bullet = _BULLET.match(line)
            if bullet:
                for hex_value in find_colours(bullet.group(1)):
                    keep(hex_value, role_of(re.sub(r"[#`()]", " ", bullet.group(1))))
    for hex_value in uses:
        keep(hex_value, "other")

    ordered = sorted(chosen, key=lambda h: (-uses[h], h))[:MAX_COLOURS]
    return [BriefColour(hex=h, role=chosen[h], weight=round(uses[h] / most, 3)) for h in ordered]


# --- Type ------------


def _weights(cell: str) -> tuple[int, ...]:
    found = {int(w) for w in re.findall(r"\b([1-9]00)\b", cell)}
    found |= {
        v for word, v in _WEIGHT_WORDS.items() if re.search(rf"\b{word}\b", cell, re.IGNORECASE)
    }
    return tuple(sorted(found))


def _font_role(label: str) -> FontRole:
    for pattern, role in _ROLE_FONT:
        if re.search(pattern, label.lower()):
            return role
    return "body"


def _fonts(sections: list[_Section], text: str) -> list[BriefFont]:
    votes: dict[FontRole, Counter[str]] = {
        "display": Counter(),
        "body": Counter(),
        "mono": Counter(),
    }
    weights: dict[tuple[FontRole, str], set[int]] = {}
    generics: dict[str, str] = {}

    def vote(role: FontRole, family: str, found: tuple[int, ...] = (), raw: str = "") -> None:
        votes[role][family] += 1
        weights.setdefault((role, family), set()).update(found)
        if raw:
            generics.setdefault(family, raw)

    for section in sections:
        if not _is(section, r"typo|type|font|tipograf"):
            continue
        for header, rows in _tables(section):
            names = [h.lower() for h in header]
            family_at = next((i for i, h in enumerate(names) if "family" in h or "font" in h), None)
            if family_at is None:
                continue
            role_at = next(
                (i for i, h in enumerate(names) if h in {"role", "style", "name", "use"}), 0
            )
            weight_at = next((i for i, h in enumerate(names) if "weight" in h), None)
            for row in rows:
                if len(row) <= family_at:
                    continue
                family = clean_family(row[family_at])
                if family:
                    found = (
                        _weights(row[weight_at])
                        if weight_at is not None and len(row) > weight_at
                        else ()
                    )
                    vote(
                        _font_role(row[role_at] if len(row) > role_at else ""),
                        family,
                        found,
                        row[family_at],
                    )

    for match in _FONT_LINE.finditer(text):
        named = re.split(r"\s+(?:for|used|with|in|as|on|and|at)\b", match.group(2).strip())[0]
        family = clean_family(named)
        if family and family.lower() not in {"the", "a", "an", "used", "and"}:
            vote(_font_role(match.group(1)), family)
    for match in _FONT_DECL.finditer(text):
        family = clean_family(match.group(1))
        if family:
            vote("body", family, raw=match.group(1))

    result: list[BriefFont] = []
    for role in ("display", "body", "mono"):
        if not votes[role]:
            continue
        family = votes[role].most_common(1)[0][0]
        found = tuple(sorted(w for w in weights.get((role, family), set()) if 400 <= w <= 700))
        category = category_of(family, generic_of(generics.get(family, "")))
        if role == "mono":
            category = "mono"
        default = {"display": (600, 700), "body": (400, 600), "mono": (400,)}[role]
        result.append(
            BriefFont(name=family, role=role, category=category, weights=found[-2:] or default)
        )
    # The same family twice (a type scale that uses one face for everything) is one
    # face: it stays the body, and the headings inherit it.
    if len(result) >= 2 and result[0].role == "display" and result[0].name == result[1].name:
        result = result[1:]
    return result


# --- Shape, motion and rules ------------


def _radius(text: str, sections: list[_Section]) -> str | None:
    values: list[str] = []
    for section in sections:
        if not _is(section, r"radius|rounded|corner|shape"):
            continue
        for _header, rows in _tables(section):
            for row in rows:
                preferred = re.search(
                    r"button|card|input|default|base|md", " ".join(row[:1]).lower()
                )
                for cell in row[1:]:
                    for number, unit in _LENGTH.findall(cell):
                        values.extend([f"{number}{unit}"] * (3 if preferred else 1))
                    if re.fullmatch(r"0(px|rem)?", cell.strip()):
                        values.append("0")
        for line in section.lines:
            if not line.strip().startswith("|"):
                values.extend(f"{n}{u}" for n, u in _LENGTH.findall(line))
    for match in _RADIUS_DECL.finditer(text):
        declared = match.group(1)
        found = [f"{n}{u}" for n, u in _LENGTH.findall(declared)]
        values.extend(found or (["0"] if re.match(r"\s*0(?![\d.])", declared) else []))
    return radius_from(values)


def _motion(text: str) -> int | None:
    lowered = text.lower()
    if re.search(r"no animation|no motion|static|motionless|instant|minimal motion", lowered):
        return 2
    if re.search(
        r"gsap|scrolltrigger|scroll-triggered|parallax|lottie|three\.js|webgl|scroll-driven",
        lowered,
    ):
        return 8
    if re.search(r"keyframe|animation|transition|fade|reveal|spring|ease-|hover", lowered):
        return 5
    return None


def _density(text: str) -> int | None:
    lowered = text.lower()
    if re.search(r"\bdense\b|\bcompact\b|data-heavy|cockpit|information-dense", lowered):
        return 7
    if re.search(r"spacious|airy|generous whitespace|breathing room|gallery", lowered):
        return 3
    return None


def _bullets(section: _Section) -> list[str]:
    items = []
    for line in section.lines:
        match = _BULLET.match(line)
        if match:
            items.append(re.sub(r"[*`]", "", match.group(1)).strip()[:240])
    return [item for item in items if item]


def _surface(colours: list[BriefColour], text: str) -> str | None:
    if re.search(r"dark (?:theme|mode|ui|interface)|dark-only|on a dark", text, re.IGNORECASE):
        return "dark"
    background = next((c for c in colours if c.role == "background"), None)
    if background is None:
        return None
    try:
        return "dark" if rgb_to_oklch(parse_hex(background.hex))[0] < 0.35 else None
    except BrandError:
        return None


def brief_from_markdown(
    text: str,
    *,
    source: Source = "brief",
    provenance: str | None = None,
) -> DesignBrief:
    """A brief from the text of a Refero, skillui or Stitch-style `DESIGN.md`."""
    if len(text.encode("utf-8")) > MAX_BYTES:
        raise BrandError("el DESIGN.md pesa demasiado para ser una referencia de estilo")
    sections = _sections(text)
    colours = _colours(text, sections)
    fonts = _fonts(sections, text)
    title = _title(text) or "Referencia"

    anti: list[str] = []
    notes: list[str] = []
    for section in sections:
        if _is(section, r"don'?t|avoid|never|anti.?pattern"):
            anti.extend(_bullets(section))
        elif _is(section, r"^do\b|do'?s\b|^dos$|principles|guidelines"):
            notes.extend(f"referencia: {item}" for item in _bullets(section))

    if not colours and not fonts:
        raise BrandError(
            "no encuentro colores ni fuentes en ese texto: ¿es un DESIGN.md de estilo "
            "(Refero, skillui)? Si es un texto libre, rellena el brief a mano "
            "(`make design-brief-schema` imprime su esquema)"
        )

    return DesignBrief(
        source=source,
        provenance=provenance or f"{title} (DESIGN.md importado)",
        title=title,
        colours=tuple(colours),
        fonts=tuple(fonts),
        radius=_radius(text, sections),
        surface=_surface(colours, text),
        density=_density(text),
        motion=_motion(text),
        keywords=(),
        ux_notes=tuple(notes[:12]),
        anti_patterns=tuple(anti[:12]),
    )
