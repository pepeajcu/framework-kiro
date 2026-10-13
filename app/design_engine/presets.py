"""Style presets: sensible defaults for every axis of the contract.

Picking a style should change the *whole* identity, not only a colour: theme,
radius, neutrals, surface, fonts, header and motion level. That way even a lazy
fill (`make design init preset=brutalista`) lands somewhere distinct from the
default, and two presets never differ in just one variable.

A preset is a starting point. `/kiro-init` then adjusts the brand colour and
adds the project's own visual signature on top (see `DESIGN.md`).

The table in `.claude/skills/kiro-design/SKILL.md` documents the same values;
`tests/test_design_engine.py` fails if the two drift apart.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.design_engine.contract import (
    Basecoat,
    Brand,
    DesignContract,
    DesignError,
    FontFace,
    Motion,
    Structure,
    Typography,
)


@dataclass(frozen=True)
class Preset:
    """A named style: dials, a reading, a reference file and a starting contract."""

    name: str
    variance: int
    motion: int
    density: int
    reads_as: str
    reference: str  # file under .claude/skills/kiro-design/references/
    contract: DesignContract


def _face(name: str, *weights: int, fallback: str | None = None) -> FontFace:
    return FontFace.model_validate({"name": name, "weights": list(weights), "fallback": fallback})


PRESETS: dict[str, Preset] = {
    "minimalista": Preset(
        name="minimalista",
        variance=5,
        motion=3,
        density=2,
        reads_as="Notion, Linear: monocromo cálido, tipografía editorial, bordes finos",
        reference="minimalist.md",
        contract=DesignContract(
            brand=Brand(primary="#292524", neutral="warm", surface="light", radius="0.5rem"),
            typography=Typography(
                display=_face("Newsreader", 400, 600, fallback="serif"),
                body=_face("Geist", 400, 600),
            ),
            basecoat=Basecoat(theme="nova"),
            motion=Motion(level=3),
            structure=Structure(header="sticky-blur"),
        ),
    ),
    "suave-premium": Preset(
        name="suave-premium",
        variance=7,
        motion=6,
        density=3,
        reads_as="Calmado y caro: sombras suaves, tarjetas anidadas, mucho aire",
        reference="soft.md",
        contract=DesignContract(
            brand=Brand(primary="#3F6B5A", neutral="warm", surface="cream", radius="1rem"),
            typography=Typography(
                display=_face("Fraunces", 400, 600, fallback="serif"),
                body=_face("Plus Jakarta Sans", 400, 600),
            ),
            basecoat=Basecoat(theme="luma"),
            motion=Motion(level=6),
            structure=Structure(header="floating-pill"),
        ),
    ),
    "brutalista": Preset(
        name="brutalista",
        variance=9,
        motion=4,
        density=6,
        reads_as="Imprenta suiza o terminal: rejilla dura, tipografía enorme, un acento de peligro",
        reference="brutalist.md",
        contract=DesignContract(
            brand=Brand(primary="#DC2626", neutral="pure", surface="light", radius="0"),
            typography=Typography(
                display=_face("Archivo Black", 400),
                body=_face("Archivo", 400, 600),
                mono=_face("JetBrains Mono", 400, fallback="mono"),
            ),
            basecoat=Basecoat(theme="lyra"),
            motion=Motion(level=4),
            structure=Structure(header="industrial-rule"),
        ),
    ),
    "institucional": Preset(
        name="institucional",
        variance=3,
        motion=2,
        density=5,
        reads_as="Confianza primero: sector público, salud, finanzas. Llano y de alto contraste",
        reference="institucional.md",
        contract=DesignContract(
            brand=Brand(primary="#1E3A8A", neutral="cool", surface="light", radius="0.375rem"),
            typography=Typography(
                display=_face("Source Serif 4", 600, 700, fallback="serif"),
                body=_face("Public Sans", 400, 600),
            ),
            basecoat=Basecoat(theme="vega"),
            motion=Motion(level=2),
            structure=Structure(header="sticky-blur"),
        ),
    ),
    "expresivo": Preset(
        name="expresivo",
        variance=9,
        motion=8,
        density=3,
        reads_as="Agencia, creativo, lanzamiento: tipografía grande, asimetría y movimiento",
        reference="expresivo.md",
        contract=DesignContract(
            brand=Brand(primary="#EA580C", neutral="tinted", surface="cream", radius="1.5rem"),
            typography=Typography(
                display=_face("Bricolage Grotesque", 600, 800),
                body=_face("Figtree", 400, 600),
            ),
            basecoat=Basecoat(theme="rhea"),
            motion=Motion(level=8),
            structure=Structure(header="custom"),
        ),
    ),
    "panel-de-datos": Preset(
        name="panel-de-datos",
        variance=3,
        motion=2,
        density=8,
        reads_as="Back-office denso: conserva el tacto de Basecoat y aprieta la densidad",
        reference="panel-de-datos.md",
        contract=DesignContract(
            brand=Brand(primary="#2563EB", neutral="cool", surface="light", radius="0.375rem"),
            typography=Typography(
                body=_face("IBM Plex Sans", 400, 600),
                mono=_face("IBM Plex Mono", 400, 500, fallback="mono"),
            ),
            basecoat=Basecoat(theme="mira"),
            motion=Motion(level=2),
            structure=Structure(header="terminal-bar"),
        ),
    ),
    "editorial": Preset(
        name="editorial",
        variance=6,
        motion=3,
        density=3,
        reads_as="Una publicación impresa: serif de titular, columna estrecha, reglas finas",
        reference="editorial.md",
        contract=DesignContract(
            brand=Brand(primary="#7F1D1D", neutral="warm", surface="cream", radius="0"),
            typography=Typography(
                display=_face("Playfair Display", 700, fallback="serif"),
                body=_face("Public Sans", 400, 600),
            ),
            basecoat=Basecoat(theme="sera"),
            motion=Motion(level=3),
            structure=Structure(header="industrial-rule"),
        ),
    ),
    "organico": Preset(
        name="organico",
        variance=6,
        motion=5,
        density=2,
        reads_as="Cálido y hecho a mano: formas blandas, tierra y verdes, serif amable",
        reference="organico.md",
        contract=DesignContract(
            brand=Brand(primary="#4D7C0F", neutral="warm", surface="cream", radius="1.25rem"),
            typography=Typography(
                display=_face("Young Serif", 400, fallback="serif"),
                body=_face("Figtree", 400, 600),
            ),
            basecoat=Basecoat(theme="maia"),
            motion=Motion(level=5),
            structure=Structure(header="floating-pill"),
        ),
    ),
    "neo-brutalista": Preset(
        name="neo-brutalista",
        variance=9,
        motion=5,
        density=6,
        reads_as="Color plano y chillón, bordes gruesos, sombras duras, tipografía condensada",
        reference="neo-brutalista.md",
        contract=DesignContract(
            brand=Brand(primary="#FACC15", neutral="pure", surface="light", radius="0"),
            typography=Typography(
                display=_face("Big Shoulders Display", 700, 800),
                body=_face("Barlow", 400, 600),
            ),
            basecoat=Basecoat(theme="lyra"),
            motion=Motion(level=5),
            structure=Structure(header="industrial-rule"),
        ),
    ),
    "retro-y2k": Preset(
        name="retro-y2k",
        variance=8,
        motion=6,
        density=4,
        reads_as="Web de 1999 con ironía: azul eléctrico, píxeles, brillos y bordes redondos",
        reference="retro-y2k.md",
        contract=DesignContract(
            brand=Brand(primary="#2F5BFF", neutral="tinted", surface="light", radius="1.5rem"),
            typography=Typography(
                display=_face("Pixelify Sans", 400, 700),
                body=_face("Rubik", 400, 500),
                mono=_face("Silkscreen", 400, fallback="mono"),
            ),
            basecoat=Basecoat(theme="luma"),
            motion=Motion(level=6),
            structure=Structure(header="floating-pill"),
        ),
    ),
    "oscuro-tecnologico": Preset(
        name="oscuro-tecnologico",
        variance=6,
        motion=5,
        density=6,
        reads_as="Herramienta de desarrollo: superficie oscura, monoespaciada, un acento frío",
        reference="oscuro-tecnologico.md",
        contract=DesignContract(
            brand=Brand(primary="#38BDF8", neutral="cool", surface="dark", radius="0.375rem"),
            typography=Typography(
                display=_face("Martian Mono", 400, 700, fallback="mono"),
                body=_face("Hanken Grotesk", 400, 600),
            ),
            basecoat=Basecoat(theme="mira"),
            motion=Motion(level=5),
            structure=Structure(header="terminal-bar"),
        ),
    ),
}


def get_preset(name: str) -> Preset:
    try:
        return PRESETS[name]
    except KeyError:
        options = " | ".join(PRESETS)
        raise DesignError(f"el estilo '{name}' no existe; opciones: {options}") from None
