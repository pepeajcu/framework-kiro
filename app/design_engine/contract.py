"""The design contract: what `design.toml` says, validated.

`design.toml` is the machine-readable half of a project's identity (the other
half is `DESIGN.md`, prose for the AI). Everything the compiler can apply lives
here; nothing here is applied until `make design build` runs.

The models are strict (`extra="forbid"`): a typo such as `primay = "#fff"` must
fail loudly instead of silently compiling the default.
"""

from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from app.branding import BrandError, parse_hex
from app.design_engine.rules import check_allowed

# The values the compiler understands. Kept as tuples so error messages, the
# skill documentation and the tests all read from one place.
THEMES = ("vega", "nova", "maia", "lyra", "mira", "luma", "sera", "rhea")
NEUTRALS = ("pure", "warm", "cool", "tinted")
SURFACES = ("light", "cream", "dark", "auto")
HEADERS = (
    "sticky-blur",
    "floating-pill",
    "industrial-rule",
    "terminal-bar",
    "ios-bar",
    "custom",
)
FALLBACKS = ("sans", "serif", "mono", "system")
KITS = ("none", "ios")

Theme = Literal["vega", "nova", "maia", "lyra", "mira", "luma", "sera", "rhea"]
Neutral = Literal["pure", "warm", "cool", "tinted"]
Surface = Literal["light", "cream", "dark", "auto"]
Header = Literal[
    "sticky-blur", "floating-pill", "industrial-rule", "terminal-bar", "ios-bar", "custom"
]
Fallback = Literal["sans", "serif", "mono", "system"]
Kit = Literal["none", "ios"]

CONTRACT_FILE = "design.toml"
DEFAULT_PRIMARY = "#171717"
DEFAULT_RADIUS = "0.625rem"  # Basecoat's own default

_RADIUS = re.compile(r"^(?:\d{1,4}(?:\.\d{1,3})?(?:rem|px|em))$")
_FONT_NAME = re.compile(r"^[A-Za-z][A-Za-z0-9 ]{0,59}$")


class DesignError(BrandError):
    """The contract, or something it needs, cannot be used. Message is for the user."""


def _normalise_hex(value: object) -> str | None:
    """`#0f6` or `0F766E` to `#0F766E`; empty means "not set"."""
    if value is None or (isinstance(value, str) and not value.strip()):
        return None
    if not isinstance(value, str):
        raise ValueError("debe ser un color hex como '#0F766E'")
    r, g, b = (round(channel * 255) for channel in parse_hex(value))
    return f"#{r:02X}{g:02X}{b:02X}"


def normalise_hex(value: object) -> str | None:
    """Public form of the colour normaliser, for briefs and importers."""
    return _normalise_hex(value)


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)


class Brand(_Strict):
    """Colour and shape: the part of the identity that becomes CSS variables."""

    primary: str = DEFAULT_PRIMARY
    neutral: Neutral = "pure"
    surface: Surface = "light"
    secondary: str | None = None
    radius: str = DEFAULT_RADIUS

    @field_validator("primary", mode="before")
    @classmethod
    def _check_primary(cls, value: object) -> str:
        normalised = _normalise_hex(value)
        if normalised is None:
            raise ValueError("el color primario no puede estar vacío")
        return normalised

    @field_validator("secondary", mode="before")
    @classmethod
    def _check_secondary(cls, value: object) -> str | None:
        return _normalise_hex(value)

    @field_validator("radius", mode="before")
    @classmethod
    def _check_radius(cls, value: object) -> object:
        if not isinstance(value, str):
            raise ValueError("debe ser un texto como '0.5rem' o '0'")
        value = value.strip()
        if value in {"0", "0rem", "0px"}:
            # A bare `0` inside Basecoat's `calc(var(--radius) - 4px)` is invalid
            # CSS (unitless zero cannot be mixed with a length in calc()).
            return "0rem"
        if not _RADIUS.match(value):
            raise ValueError(f"'{value}' no es un radio válido (ej. 0.5rem, 8px, 0)")
        return value


class FontFace(_Strict):
    """One family and the weights the project ships. Always local woff2 (ADR-0005)."""

    name: str
    weights: tuple[int, ...] = (400,)
    fallback: Fallback | None = None

    @field_validator("name")
    @classmethod
    def _check_name(cls, value: str) -> str:
        value = " ".join(value.split())
        if not _FONT_NAME.match(value):
            raise ValueError(
                f"'{value}' no es un nombre de familia válido (letras, números y espacios)"
            )
        return value

    @field_validator("weights", mode="before")
    @classmethod
    def _check_weights(cls, value: object) -> object:
        if not isinstance(value, list | tuple) or not value:
            raise ValueError("debe ser una lista de pesos, ej. [400, 700]")
        weights: set[int] = set()
        for item in value:
            try:
                weight = int(item)
            except (TypeError, ValueError) as exc:
                raise ValueError(f"'{item}' no es un peso válido") from exc
            if weight not in range(100, 1000, 100):
                raise ValueError(f"el peso {weight} no es válido (100, 200 … 900)")
            weights.add(weight)
        return tuple(sorted(weights))

    @property
    def slug(self) -> str:
        """Fontsource id: `Plus Jakarta Sans` becomes `plus-jakarta-sans`."""
        return font_slug(self.name)


def font_slug(name: str) -> str:
    return "-".join(name.lower().split())


class Typography(_Strict):
    """The `[type]` table. All three roles are optional: Basecoat's stack remains."""

    display: FontFace | None = None
    body: FontFace | None = None
    mono: FontFace | None = None

    def faces(self) -> tuple[tuple[str, FontFace], ...]:
        """`(role, face)` for every declared role, in a stable order."""
        return tuple(
            (role, face)
            for role, face in (
                ("display", self.display),
                ("body", self.body),
                ("mono", self.mono),
            )
            if face is not None
        )


class Basecoat(_Strict):
    theme: Theme = "vega"


class Motion(_Strict):
    level: int = Field(default=3, ge=1, le=10)


class Structure(_Strict):
    header: Header = "sticky-blur"
    #: A platform kit: its own components, materials and type scale (`app.design_engine.kits`).
    kit: Kit = "none"
    #: VISUAL_DENSITY: 1 is a gallery, 10 a cockpit. Compiled to the rhythm (`rhythm.py`).
    density: int = Field(default=5, ge=1, le=10)


class Rules(_Strict):
    """`[rules]`: design rules this project turns off on purpose.

    Only taste can be allowed (see `app.design_engine.rules`); accessibility,
    touch and performance are not negotiable. Allowing a rule is a decision, so
    `design-check` reports it on every run instead of staying silent.
    """

    allow: tuple[str, ...] = ()

    @field_validator("allow", mode="before")
    @classmethod
    def _check_allow(cls, value: object) -> tuple[str, ...]:
        if not isinstance(value, list | tuple):
            raise ValueError('debe ser una lista, ej. ["P1", "P2"]')
        ids = tuple(sorted({str(item).strip().upper() for item in value}))
        check_allowed(ids)
        return ids


class DesignContract(_Strict):
    """The whole of `design.toml`."""

    brand: Brand = Field(default_factory=Brand)
    typography: Typography = Field(default_factory=Typography, alias="type")
    basecoat: Basecoat = Field(default_factory=Basecoat)
    motion: Motion = Field(default_factory=Motion)
    structure: Structure = Field(default_factory=Structure)
    rules: Rules = Field(default_factory=Rules)

    @property
    def is_default(self) -> bool:
        """Still exactly what ships with the framework (potential convergence)."""
        return self == DesignContract()


# --- Reading ----------------------------------------------------------------


def _format_errors(exc: ValidationError, source: str = "design.toml") -> str:
    lines: list[str] = []
    for error in exc.errors():
        where = ".".join(str(part) for part in error["loc"]) or "(raíz)"
        kind = error["type"]
        if kind == "literal_error":
            expected = error.get("ctx", {}).get("expected", "")
            options = expected.replace("'", "").replace(" or ", " | ").replace(", ", " | ")
            message = f"valor no válido; opciones: {options}"
        elif kind == "extra_forbidden":
            message = "clave desconocida (¿errata?)"
        elif kind == "missing":
            message = "falta este campo"
        elif kind == "greater_than_equal":
            message = f"debe ser al menos {error.get('ctx', {}).get('ge')}"
        elif kind == "less_than_equal":
            message = f"debe ser como mucho {error.get('ctx', {}).get('le')}"
        elif kind == "value_error":
            message = str(error["msg"]).removeprefix("Value error, ")
        else:
            message = str(error["msg"])
        lines.append(f"  - {where}: {message}")
    count = len(lines)
    head = f"{source} tiene 1 error:" if count == 1 else f"{source} tiene {count} errores:"
    return "\n".join([head, *lines])


def parse_contract(text: str) -> DesignContract:
    """Parse and validate the contents of a `design.toml`."""
    try:
        data = tomllib.loads(text)
    except tomllib.TOMLDecodeError as exc:
        raise DesignError(f"design.toml no es TOML válido: {exc}") from exc
    try:
        return DesignContract.model_validate(data)
    except ValidationError as exc:
        raise DesignError(_format_errors(exc)) from exc


def contract_from_data(data: dict[str, Any]) -> DesignContract:
    """Validate a plain dict as a contract, with the same messages as `design.toml`.

    The scripts edit the contract as data (`brand.primary=...`); every edit goes
    through here so a bad value reads like a bad toml, never like a traceback.
    """
    try:
        return DesignContract.model_validate(data)
    except ValidationError as exc:
        raise DesignError(_format_errors(exc)) from exc


def font_face_from_values(name: str, weights: list[int], fallback: str | None) -> FontFace:
    """A `FontFace` from command-line values, failing like a bad `design.toml`."""
    try:
        return FontFace.model_validate({"name": name, "weights": weights, "fallback": fallback})
    except ValidationError as exc:
        raise DesignError(_format_errors(exc, "la fuente indicada")) from exc


def load_contract(path: Path) -> DesignContract:
    """Read `design.toml`. A missing file means the defaults, not an error."""
    if not path.is_file():
        return DesignContract()
    return parse_contract(path.read_text(encoding="utf-8"))


# --- Writing ----------------------------------------------------------------


def _q(value: str) -> str:
    """A TOML basic string. JSON string syntax is a subset of it."""
    return json.dumps(value, ensure_ascii=True)


def _face_line(role: str, face: FontFace | None, comment: str) -> str:
    if face is None:
        return f'# {role:<8}= {{ name = "Nombre", weights = [400, 700] }}   # {comment}'
    parts = [f"name = {_q(face.name)}", f"weights = [{', '.join(map(str, face.weights))}]"]
    if face.fallback:
        parts.append(f"fallback = {_q(face.fallback)}")
    return f"{role:<10}= {{ {', '.join(parts)} }}"


def dump_contract(contract: DesignContract) -> str:
    """The canonical `design.toml`, with the comments that explain each key.

    Shortcuts such as `make brand-colors` rewrite the file in this form, so a
    hand-written comment of your own does not survive them. Keep prose in
    `DESIGN.md`.
    """
    brand, typo = contract.brand, contract.typography
    secondary = _q(brand.secondary) if brand.secondary else '""'
    lines = [
        "# Contrato de diseño del proyecto. Lo compila `make design build`.",
        "# La intención (tono, referencias, firma visual) vive en DESIGN.md; aquí solo",
        "# lo que una máquina puede aplicar. Atajos que lo reescriben: `make brand-colors`,",
        "# `make font`. Verifícalo con `make design-check`.",
        "",
        "[brand]",
        f"primary   = {_q(brand.primary)}",
        f"neutral   = {_q(brand.neutral)}   # {' | '.join(NEUTRALS)}",
        f"surface   = {_q(brand.surface)}   # {' | '.join(SURFACES)}",
        f"secondary = {secondary}   # opcional: un segundo color de marca",
        f"radius    = {_q(brand.radius)}",
        "",
        "[type]",
        "# Fuentes de Fontsource, siempre locales (woff2 en app/static/fonts/).",
        _face_line("display", typo.display, "titulares"),
        _face_line("body", typo.body, "texto"),
        _face_line("mono", typo.mono, "código y datos"),
        "",
        "[basecoat]",
        f"theme = {_q(contract.basecoat.theme)}   # {' | '.join(THEMES)}",
        "",
        "[motion]",
        f"level = {contract.motion.level}   # 1-3 CSS · 4-6 motion.js · 7-8 Motion · 9-10 GSAP",
        "",
        "[structure]",
        f"header = {_q(contract.structure.header)}   # {' | '.join(HEADERS)}",
    ]
    if contract.structure.kit != "none":
        # Only written when used, like [rules]: most projects have no kit.
        lines.append(f"kit    = {_q(contract.structure.kit)}   # {' | '.join(KITS)}")
    if contract.structure.density != 5:
        # Only written when it is not the middle: 1 airy (a gallery) ... 10 packed (a cockpit).
        lines.append(f"density = {contract.structure.density}   # 1 aireado ... 10 denso")
    lines.append("")
    if contract.rules.allow:
        # Only written when used: most projects never turn a rule off, and the
        # file stays as short as the contract it describes.
        allowed = ", ".join(_q(rule_id) for rule_id in contract.rules.allow)
        lines += [
            "[rules]",
            f"allow = [{allowed}]   # reglas de gusto permitidas a propósito (ver DESIGN.md)",
            "",
        ]
    return "\n".join(lines)


def contract_to_data(contract: DesignContract) -> dict[str, Any]:
    """Plain-dict form, handy for tests and for the preview endpoint."""
    return contract.model_dump(by_alias=True, mode="python")
