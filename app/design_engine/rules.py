"""The design rules, in one table.

`make design-check`, the UX-floor tests and the report of `/kiro-design-review`
talk about the same rules, so they share these identifiers. A rule is one line
here and nowhere else; the code that detects it lives next to what it inspects.

**Categories are the ten of the uupm guide, in its priority order** (see
`.claude/skills/kiro-design/references/constitution.md`). The first three are the
floor: accessibility, touch and performance. They are never relaxed, whatever
`DESIGN.md` or `design.toml` say. The rest are taste and can be allowed, on
purpose, in `[rules] allow` of `design.toml`.

Two groups exist today:

- `D*` the contract and the build (colour contrast, a stale `input.css`, a font
  that is not there...). Checked by `design-check`.
- `P*` generic patterns: the page shapes that make a project look like every
  other one. Warnings, relaxable.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Owner = Literal["contract", "platform", "uupm", "taste"]
Severity = Literal["error", "warn"]

#: uupm's categories, by priority. Priority 1 is the highest.
CATEGORIES: dict[int, str] = {
    1: "Accesibilidad",
    2: "Táctil e interacción",
    3: "Rendimiento",
    4: "Selección de estilo",
    5: "Layout y responsive",
    6: "Tipografía y color",
    7: "Animación",
    8: "Formularios y feedback",
    9: "Navegación",
    10: "Gráficos y datos",
}

#: Categories whose rules cannot be relaxed by a project.
FLOOR = frozenset({1, 2, 3})


@dataclass(frozen=True)
class DesignRule:
    id: str
    category: int
    owner: Owner
    severity: Severity
    title: str
    fix: str

    @property
    def relaxable(self) -> bool:
        return self.category not in FLOOR


def _rule(
    rule_id: str, category: int, owner: Owner, severity: Severity, title: str, fix: str
) -> tuple[str, DesignRule]:
    return rule_id, DesignRule(rule_id, category, owner, severity, title, fix)


RULES: dict[str, DesignRule] = dict(
    (
        # --- The contract and the build -------------------------------------------
        _rule(
            "D1",
            1,
            "contract",
            "error",
            "un par de colores no llega a contraste WCAG AA",
            "usa el hex que propone el compilador, o cambia el color de marca",
        ),
        _rule(
            "D2",
            3,
            "platform",
            "error",
            "input.css no está al día con design.toml",
            "ejecuta `make design build`",
        ),
        _rule(
            "D3",
            3,
            "platform",
            "error",
            "falta una fuente o un archivo de motion que design.toml declara",
            "ejecuta `make design build`; las fuentes son locales (ADR-0005)",
        ),
        _rule(
            "D4",
            7,
            "contract",
            "warn",
            "un data-motion pide más nivel del que tiene el proyecto",
            "sube motion.level en design.toml o quita el atributo",
        ),
        _rule(
            "D5",
            4,
            "taste",
            "warn",
            "DESIGN.md y design.toml se contradicen, o falta la firma visual",
            "actualiza el que esté desfasado; sin firma el proyecto converge con otros",
        ),
        _rule(
            "D6",
            4,
            "platform",
            "warn",
            "hay otra skill de diseño que compite con kiro-design",
            "kiro-design es la única; uupm y taste ya están vendorizados como referencias",
        ),
        # --- Generic patterns ----------------------------------------------------------
        _rule(
            "P1",
            5,
            "taste",
            "warn",
            "titular centrado seguido de tres tarjetas iguales",
            "elige otro arquetipo de references/archetypes.md (split, bento, editorial...)",
        ),
        _rule(
            "P2",
            5,
            "taste",
            "warn",
            "muro de logos o franja de «confían en nosotros»",
            "pon las señales de confianza bajo el hero, con datos reales (logo-row, spec-sheet)",
        ),
        _rule(
            "P3",
            5,
            "taste",
            "warn",
            "carrusel de testimonios",
            "cita dos o tres testimonios con nombre y contexto, sin carrusel",
        ),
        _rule(
            "P4",
            5,
            "taste",
            "warn",
            "precios en tres columnas idénticas",
            "destaca un plan, o presenta la comparación como tabla (spec-sheet)",
        ),
        _rule(
            "P5",
            5,
            "taste",
            "warn",
            "h-screen (en móvil el navegador recorta la altura)",
            "usa min-h-[100dvh]",
        ),
        _rule(
            "P6",
            5,
            "taste",
            "warn",
            "backdrop-blur en un elemento que no es una barra fija o sticky",
            "el desenfoque va solo en barras fijas; en contenido que se desplaza es lento",
        ),
        _rule(
            "P7",
            4,
            "taste",
            "warn",
            "emoji en el marcado",
            "usa un SVG con un solo grosor de trazo",
        ),
        _rule(
            "P8",
            4,
            "taste",
            "warn",
            "vocabulario de plantilla de IA (Elevate, Seamless, Unleash, Next-Gen...)",
            "di lo que hace el producto, con las palabras de PROJECT.md",
        ),
        _rule(
            "P9",
            4,
            "taste",
            "warn",
            "raya larga (—) en un texto visible",
            "usa una coma, dos puntos o dos frases",
        ),
        _rule(
            "P10",
            4,
            "taste",
            "warn",
            "nombre de relleno (John Doe, Acme, Lorem ipsum)",
            "usa el dominio real de PROJECT.md",
        ),
    )
)

#: The ids a project may allow in `[rules] allow`.
RELAXABLE = tuple(rule.id for rule in RULES.values() if rule.relaxable)

#: What `estandar-shadcn` allows: every generic-pattern rule.
GENERIC_PATTERNS = tuple(rule_id for rule_id in RULES if rule_id.startswith("P"))


def check_allowed(ids: tuple[str, ...]) -> None:
    """Raise `ValueError` (in Spanish, for the user) if an id cannot be relaxed."""
    for rule_id in ids:
        rule = RULES.get(rule_id)
        if rule is None:
            raise ValueError(
                f"'{rule_id}' no es una regla; las que se pueden permitir: {options()}"
            )
        if not rule.relaxable:
            raise ValueError(
                f"'{rule_id}' ({CATEGORIES[rule.category]}) no se puede permitir: "
                "accesibilidad, uso táctil y rendimiento no se relajan nunca"
            )


def options() -> str:
    return ", ".join(RELAXABLE)
