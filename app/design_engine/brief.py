"""A design brief, and how it becomes a proposal for the contract.

Every source of visual direction (a preset, the uupm advisor, a pasted brief, an
extracted reference site) is reduced to the same object, a `DesignBrief`. One pure
function, `propose`, filters and translates it into a contract; nothing else in
the engine knows where a brief came from. That is what keeps five sources from
becoming five pipelines with five sets of bugs (ADR-0018).

`propose` never writes anything and never raises for a source that "does not fit":
what cannot be translated is substituted by the nearest thing the platform can do
and written down as a `Decision`, or listed as `unresolved`. Nothing is dropped in
silence.

Who owns what (the ten categories of the uupm guide) is in
`references/constitution.md`. In short: a source may propose style (colour, type,
shape, motion), but never the floor (contrast, touch size, performance), which the
compiler enforces whatever the brief says.
"""

from __future__ import annotations

import datetime as dt
import re
from collections.abc import Mapping
from dataclasses import asdict, dataclass, field
from typing import Literal, get_args

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from app.branding import parse_hex, rgb_to_oklch
from app.design_engine.contract import (
    Brand,
    DesignContract,
    DesignError,
    Fallback,
    Header,
    Neutral,
    Surface,
    Theme,
    contract_from_data,
    contract_to_data,
    normalise_hex,
)
from app.design_engine.palette import derive_palette, suggest_primary
from app.design_engine.presets import PRESETS

Source = Literal["preset", "advisor", "brief", "reference"]
ColourRole = Literal["primary", "accent", "secondary", "background", "surface", "text", "other"]
FontRole = Literal["display", "body", "mono"]

#: Below this OKLCH chroma a colour is a neutral, not a brand colour.
NEUTRAL_CHROMA = 0.04
#: One scale of corners, kept inside what Basecoat's themes were drawn for.
MAX_RADIUS_REM = 2.0

#: A font that is always installable, by category: what a source's font becomes
#: when it has no equivalent in the table the caller vouches for. All three are
#: used by a preset, so they are in `type-pairings.md`.
CATEGORY_FALLBACK: dict[Fallback, str] = {
    "sans": "Public Sans",
    "serif": "Source Serif 4",
    "mono": "JetBrains Mono",
}


class _Frozen(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class BriefColour(_Frozen):
    hex: str
    role: ColourRole = "other"
    #: Share of use in the source, 0 to 1. Used to pick the accent.
    weight: float = Field(default=0.0, ge=0.0, le=1.0)

    @field_validator("hex", mode="before")
    @classmethod
    def _check_hex(cls, value: object) -> str:
        normalised = normalise_hex(value)
        if normalised is None:
            raise ValueError("el color no puede estar vacío")
        return normalised


class BriefFont(_Frozen):
    name: str = Field(min_length=1, max_length=60)
    role: FontRole
    category: Fallback | None = None
    weights: tuple[int, ...] = (400,)


class DesignBrief(_Frozen):
    source: Source
    #: Where it came from: a URL, a file, a style name. Goes into DESIGN.md.
    provenance: str = Field(min_length=1)
    title: str = ""
    colours: tuple[BriefColour, ...] = ()
    fonts: tuple[BriefFont, ...] = ()
    #: A CSS length: `0.5rem`, `8px`, `0`.
    radius: str | None = None
    neutral: Neutral | None = None
    surface: Surface | None = None
    theme: Theme | None = None
    header: Header | None = None
    density: int | None = Field(default=None, ge=1, le=10)
    motion: int | None = Field(default=None, ge=1, le=10)
    keywords: tuple[str, ...] = ()
    #: UX advice and anti-patterns carried over for the review, never for tokens.
    ux_notes: tuple[str, ...] = ()
    anti_patterns: tuple[str, ...] = ()


@dataclass(frozen=True)
class Decision:
    """One thing the translation changed, and why."""

    field: str
    before: str
    after: str
    reason: str
    rule: str | None = None


@dataclass(frozen=True)
class Proposal:
    contract: DesignContract
    decisions: tuple[Decision, ...] = ()
    #: Things no translation could settle: a person decides.
    unresolved: tuple[str, ...] = ()
    #: Observations that are not changes (the accents that were left out...).
    notes: tuple[str, ...] = ()
    provenance: tuple[str, ...] = ()
    ux_notes: tuple[str, ...] = ()
    anti_patterns: tuple[str, ...] = ()
    keywords: tuple[str, ...] = ()
    inputs: tuple[Source, ...] = field(default=())


# --- Pieces ------------

_LENGTH = re.compile(r"^\s*(\d+(?:\.\d+)?)\s*(rem|em|px)\s*$")


def css_length_to_rem(value: str) -> float | None:
    """A CSS length in rem (16 px per rem), or None if it is not one."""
    if value.strip() in {"0", "0px", "0rem"}:
        return 0.0
    match = _LENGTH.match(value)
    if match is None:
        return None
    number = float(match.group(1))
    return number / 16 if match.group(2) == "px" else number


def format_rem(rem: float) -> str:
    return "0rem" if rem <= 0 else f"{round(rem, 3):g}rem"


def theme_for(radius_rem: float, density: int) -> Theme:
    """The Basecoat theme whose shape suits a corner radius and a density.

    The theme is the single biggest lever on how components feel (see the table
    in the kiro-design skill); radius is the clearest thing a source tells us
    about it, and density separates the tool-like themes from the quiet ones.
    """
    if radius_rem <= 0:
        return "lyra"
    if radius_rem <= 0.375:
        return "mira" if density >= 7 else "vega"
    if radius_rem <= 0.625:
        return "nova"
    if radius_rem <= 1.0:
        return "maia"
    if radius_rem <= 1.25:
        return "luma"
    return "rhea"


def _chromatic(colour: BriefColour) -> bool:
    return rgb_to_oklch(parse_hex(colour.hex))[1] >= NEUTRAL_CHROMA


def _merge(base: DesignBrief | None, inspiration: DesignBrief | None) -> DesignBrief | None:
    """The inspiration decides style; the base fills what it leaves open."""
    briefs = [b for b in (base, inspiration) if b is not None]
    if not briefs:
        return None
    if len(briefs) == 1:
        return briefs[0]
    low, high = briefs

    def pick(name: str) -> object:
        return getattr(high, name) if getattr(high, name) not in (None, ()) else getattr(low, name)

    def both(name: str) -> tuple[str, ...]:
        seen: dict[str, None] = {}
        for item in (*getattr(low, name), *getattr(high, name)):
            seen.setdefault(item)
        return tuple(seen)

    return DesignBrief.model_validate(
        {
            "source": high.source,
            "provenance": f"{low.provenance} + {high.provenance}",
            "title": high.title or low.title,
            "colours": pick("colours"),
            "fonts": pick("fonts"),
            "radius": pick("radius"),
            "neutral": pick("neutral"),
            "surface": pick("surface"),
            "theme": pick("theme"),
            "header": pick("header"),
            "density": pick("density"),
            "motion": pick("motion"),
            "keywords": both("keywords"),
            "ux_notes": both("ux_notes"),
            "anti_patterns": both("anti_patterns"),
        }
    )


def _known_families(extra: Mapping[str, str]) -> set[str]:
    """Families a proposal may name without a vouching table: the presets' own."""
    names = {
        face.name for preset in PRESETS.values() for _, face in preset.contract.typography.faces()
    }
    return names | set(extra.values())


# --- The function ------------


def propose(
    *,
    base: DesignBrief | None = None,
    inspiration: DesignBrief | None = None,
    current: DesignContract | None = None,
    fonts: Mapping[str, str] | None = None,
) -> Proposal:
    """Translate briefs into a contract proposal. Pure: it reads and returns.

    `base` is the product baseline (what uupm advises for this kind of product),
    `inspiration` is a style to wear on top of it (a preset, a pasted brief, a
    reference site). The inspiration may replace anything that is style; the
    base fills the rest. `current` is the project's contract: whatever neither
    brief says stays as it is, and `[rules] allow` is always kept.

    `fonts` maps a source's font name (case-insensitive) to the Fontsource family
    that stands in for it. Without an entry, a font becomes the catalogue font of
    its category and the substitution is recorded.
    """
    fonts = {key.casefold(): value for key, value in (fonts or {}).items()}
    contract = current or DesignContract()
    data = contract_to_data(contract)
    brief = _merge(base, inspiration)
    decisions: list[Decision] = []
    unresolved: list[str] = []
    notes: list[str] = []

    if brief is None:
        return Proposal(contract=contract, notes=("no había nada que proponer",))

    # --- Colour: one accent ------------
    candidates = [c for c in brief.colours if _chromatic(c) or c.role in ("primary", "accent")]
    ranked = sorted(
        candidates,
        key=lambda c: (c.role not in ("primary", "accent"), -c.weight),
    )
    accent = next((c for c in ranked if c.role != "secondary"), None)
    if accent is None:
        if brief.colours:
            unresolved.append("ningún color de la fuente se puede usar como acento; elige uno")
    else:
        data["brand"]["primary"] = accent.hex
        leftovers = [c.hex for c in ranked if c.role != "secondary" and c is not accent]
        if leftovers:
            notes.append(
                f"Se queda un solo acento ({accent.hex}); descartados: {', '.join(leftovers)}"
            )
    second = next((c for c in ranked if c.role == "secondary"), None)
    if second is not None:
        data["brand"]["secondary"] = second.hex
    for hint in ("neutral", "surface"):
        value = getattr(brief, hint)
        if value is not None:
            data["brand"][hint] = value

    # --- Shape: radius and theme ------------
    radius_rem: float | None = None
    if brief.radius is not None:
        radius_rem = css_length_to_rem(brief.radius)
        if radius_rem is None:
            unresolved.append(f"el radio '{brief.radius}' no es una longitud CSS (rem, em o px)")
        else:
            clamped = min(radius_rem, MAX_RADIUS_REM)
            if clamped != radius_rem:
                decisions.append(
                    Decision(
                        "brand.radius",
                        brief.radius,
                        format_rem(clamped),
                        f"se limita a {MAX_RADIUS_REM:g}rem: los temas de Basecoat "
                        "no están dibujados para más",
                    )
                )
            radius_rem = clamped
            data["brand"]["radius"] = format_rem(clamped)
    effective_rem = (
        radius_rem
        if radius_rem is not None
        else css_length_to_rem(str(data["brand"]["radius"])) or 0.0
    )

    if brief.theme is not None:
        data["basecoat"]["theme"] = brief.theme
    elif radius_rem is not None:
        density = brief.density or 5
        derived = theme_for(effective_rem, density)
        if derived != data["basecoat"]["theme"]:
            decisions.append(
                Decision(
                    "basecoat.theme",
                    str(data["basecoat"]["theme"]),
                    derived,
                    f"derivado del radio {format_rem(effective_rem)} y la densidad {density}",
                )
            )
        data["basecoat"]["theme"] = derived

    if brief.header is not None:
        data["structure"]["header"] = brief.header
    if brief.motion is not None:
        data["motion"]["level"] = brief.motion
    if brief.density is not None:
        data["structure"]["density"] = brief.density

    # --- Type: Fontsource families ------------
    known = _known_families(fonts)
    for font in brief.fonts:
        chosen = fonts.get(font.name.casefold())
        if chosen is None and font.name in known:
            chosen = font.name
        reason = ""
        if chosen is None:
            category = font.category or ("mono" if font.role == "mono" else "sans")
            chosen = CATEGORY_FALLBACK[category]
            reason = f"sin equivalente conocido en Fontsource; la de la categoría {category}"
        elif chosen != font.name:
            reason = "equivalente en Fontsource"
        if reason:
            decisions.append(Decision(f"type.{font.role}", font.name, chosen, reason))
        data["type"][font.role] = {
            "name": chosen,
            "weights": list(font.weights),
            "fallback": font.category if font.category in ("serif", "mono") else None,
        }

    # --- Contrast: the floor does not move ------------
    data, decisions, unresolved = _settle_contrast(data, decisions, unresolved)

    try:
        result = contract_from_data(data)
    except DesignError as exc:
        unresolved.append(str(exc))
        result = contract

    return Proposal(
        contract=result,
        decisions=tuple(decisions),
        unresolved=tuple(unresolved),
        notes=tuple(notes),
        provenance=tuple(b.provenance for b in (base, inspiration) if b is not None),
        ux_notes=brief.ux_notes,
        anti_patterns=brief.anti_patterns,
        keywords=brief.keywords,
        inputs=tuple(b.source for b in (base, inspiration) if b is not None),
    )


def _settle_contrast(
    data: dict[str, dict[str, object]],
    decisions: list[Decision],
    unresolved: list[str],
) -> tuple[dict[str, dict[str, object]], list[Decision], list[str]]:
    """Make the brand colours readable (WCAG AA), or say they cannot be.

    The primary is settled first and on its own; the secondary is then checked
    against the primary as it ended up, not as it came.
    """
    for key in ("primary", "secondary"):
        colour = data["brand"].get(key)
        if not colour:
            continue
        probe = {**data["brand"]}
        if key == "primary":
            probe["secondary"] = None
        try:
            failing = derive_palette(Brand.model_validate(probe)).failures
        except (ValidationError, DesignError):
            continue
        if not failing:
            continue
        suggestion = suggest_primary(str(colour))
        if suggestion is None or suggestion == colour:
            unresolved.append(f"{colour} no llega a contraste AA y no hay un hex cercano que sí")
            continue
        decisions.append(
            Decision(
                f"brand.{key}",
                str(colour),
                suggestion,
                "el texto del botón no llegaba a contraste AA con ese color",
                rule="D1",
            )
        )
        data["brand"][key] = suggestion
    return data, decisions, unresolved


# --- Saving a proposal ----------

PROPOSAL_VERSION = 1


def proposal_to_data(proposal: Proposal, created: dt.date) -> dict[str, object]:
    """A proposal as plain JSON-able data, for `.design/proposals/<name>.json`."""
    return {
        "version": PROPOSAL_VERSION,
        "created": created.isoformat(),
        "contract": contract_to_data(proposal.contract),
        "decisions": [asdict(d) for d in proposal.decisions],
        "unresolved": list(proposal.unresolved),
        "notes": list(proposal.notes),
        "provenance": list(proposal.provenance),
        "inputs": list(proposal.inputs),
        "ux_notes": list(proposal.ux_notes),
        "anti_patterns": list(proposal.anti_patterns),
        "keywords": list(proposal.keywords),
    }


def _strings(data: Mapping[str, object], key: str) -> tuple[str, ...]:
    value = data.get(key, [])
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise DesignError(f"la propuesta tiene '{key}' mal formado: debe ser una lista de textos")
    return tuple(value)


def _decisions(data: Mapping[str, object]) -> tuple[Decision, ...]:
    raw = data.get("decisions", [])
    if not isinstance(raw, list):
        raise DesignError("la propuesta tiene 'decisions' mal formado")
    try:
        return tuple(Decision(**item) for item in raw)
    except TypeError as exc:
        raise DesignError(f"la propuesta tiene una decisión mal formada ({exc})") from exc


def proposal_from_data(data: Mapping[str, object]) -> Proposal:
    """The inverse of `proposal_to_data`. The contract is validated again.

    A proposal is a file on disk that a person may have edited; what is applied is
    what passes the same validation as `design.toml`, never what it claims to be.
    """
    if data.get("version") != PROPOSAL_VERSION:
        raise DesignError("esa propuesta es de otra versión del motor; vuelve a generarla")
    raw_contract = data.get("contract")
    if not isinstance(raw_contract, dict):
        raise DesignError("la propuesta no trae el contrato")
    inputs = _strings(data, "inputs")
    if not set(inputs) <= set(get_args(Source)):
        raise DesignError(f"la propuesta tiene fuentes desconocidas: {', '.join(inputs)}")
    return Proposal(
        contract=contract_from_data(raw_contract),
        decisions=_decisions(data),
        unresolved=_strings(data, "unresolved"),
        notes=_strings(data, "notes"),
        provenance=_strings(data, "provenance"),
        inputs=tuple(item for item in inputs if item in get_args(Source)),  # type: ignore[misc]
        ux_notes=_strings(data, "ux_notes"),
        anti_patterns=_strings(data, "anti_patterns"),
        keywords=_strings(data, "keywords"),
    )


# --- Reports ------------


def provenance_entry(proposal: Proposal, today: dt.date) -> str:
    """The line that goes to DESIGN.md, under «Procedencia»."""
    sources = ", ".join(proposal.inputs) or "preset"
    where = "; ".join(proposal.provenance)
    return (
        f"- {today.isoformat()} · {sources} · {where}. "
        "Se tomó el lenguaje visual; ni logos, ni imágenes, ni código, ni fuentes de pago."
    )


def decision_lines(proposal: Proposal, today: dt.date) -> list[str]:
    """The lines that go to DESIGN.md, under «Decisiones de diseño»."""
    lines = []
    for item in proposal.decisions:
        rule = f" [{item.rule}]" if item.rule else ""
        lines.append(
            f"- {today.isoformat()} · `{item.field}`{rule}: {item.before} → {item.after} "
            f"({item.reason})"
        )
    lines += [f"- {today.isoformat()} · nota: {note}" for note in proposal.notes]
    return lines


def _show(value: object) -> str:
    """A contract value as a person reads it, not as Python prints it."""
    if value is None or value == () or value == "":
        return "(vacío)"
    if isinstance(value, dict) and "name" in value:
        weights = ",".join(str(w) for w in value.get("weights", ()))
        return f"`{value['name']}` {weights}"
    if isinstance(value, tuple | list):
        return ", ".join(str(item) for item in value)
    return f"`{value}`"


def render_report(proposal: Proposal, current: DesignContract, today: dt.date) -> str:
    """The proposal as Markdown: what would change, what was decided, what is open."""
    before, after = contract_to_data(current), contract_to_data(proposal.contract)
    changes: list[str] = []
    for section in after:
        for key, value in after[section].items():
            old = before[section].get(key)
            if old != value:
                changes.append(f"| `{section}.{key}` | {_show(old)} | {_show(value)} |")
    parts = [
        f"# Propuesta de diseño · {today.isoformat()}",
        "",
        f"Fuentes: {', '.join(proposal.inputs) or 'ninguna'} ({'; '.join(proposal.provenance)})",
        "",
        "## Cambios en design.toml",
        "",
    ]
    if changes:
        parts += ["| Clave | Antes | Después |", "|---|---|---|", *changes]
    else:
        parts.append("Ninguno: el contrato actual ya coincide.")
    if proposal.decisions or proposal.notes:
        parts += ["", "## Decisiones", "", *decision_lines(proposal, today)]
    if proposal.unresolved:
        parts += ["", "## Sin resolver (decide una persona)", ""]
        parts += [f"- {item}" for item in proposal.unresolved]
    if proposal.ux_notes:
        parts += ["", "## Notas de UX para la revisión", ""] + [f"- {n}" for n in proposal.ux_notes]
    if proposal.anti_patterns:
        parts += ["", "## Anti-patrones a evitar", ""] + [f"- {n}" for n in proposal.anti_patterns]
    parts += ["", "Se aplica con `make design-apply proposal=<nombre>`.", ""]
    return "\n".join(parts)
