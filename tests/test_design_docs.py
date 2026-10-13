"""The documentation the AI reads must say what the code does.

The skill, the references and the commands are instructions: if they name a
make target that does not exist, a font that cannot be installed or a contract
that differs from the preset, the AI follows them and fails. These tests turn
each of those claims into something that can break the build.
"""

from __future__ import annotations

import re
from html.parser import HTMLParser
from pathlib import Path
from typing import ClassVar

import pytest

from app.design_engine.contract import FontFace, dump_contract
from app.design_engine.presets import PRESETS

REPO = Path(__file__).resolve().parent.parent
SKILL_DIR = REPO / ".claude/skills/kiro-design"
REFERENCES = SKILL_DIR / "references"
COMMANDS = REPO / ".claude/commands"

# The three style references vendored from taste-skill; the rest are written for Kiro.
VENDORED = {"minimalist.md", "soft.md", "brutalist.md", "redesign.md", "brandkit.md"}
KIRO_STYLES = [name for name, p in PRESETS.items() if p.reference not in VENDORED]


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


# --- References -------------------------------------------------------------


@pytest.mark.parametrize("name", KIRO_STYLES)
def test_a_style_reference_embeds_exactly_its_presets_contract(name: str) -> None:
    """The toml block in the reference is the one `make design-init` writes."""
    preset = PRESETS[name]
    contract_block = dump_contract(preset.contract).split("\n\n", 1)[1].rstrip("\n")

    assert contract_block in read(REFERENCES / preset.reference), (
        f"{preset.reference} ya no coincide con el preset '{name}'; regenera el bloque"
    )
    assert f"make design-init preset={name}" in read(REFERENCES / preset.reference)


def test_there_are_eleven_styles_and_the_five_new_ones_have_references() -> None:
    assert len(PRESETS) == 11
    assert {"editorial", "organico", "neo-brutalista", "retro-y2k", "oscuro-tecnologico"} <= set(
        PRESETS
    )
    assert set(KIRO_STYLES) == {
        "institucional",
        "expresivo",
        "panel-de-datos",
        "editorial",
        "organico",
        "neo-brutalista",
        "retro-y2k",
        "oscuro-tecnologico",
    }


def test_every_reference_file_is_known_to_the_skill_and_the_notice() -> None:
    skill = read(SKILL_DIR / "SKILL.md")
    notice = read(REFERENCES / "NOTICE.md")

    for path in sorted(REFERENCES.glob("*.md")):
        if path.name == "NOTICE.md":
            continue
        assert path.name in skill or path.name in {"redesign.md", "brandkit.md"}, (
            f"{path.name} no se menciona en SKILL.md"
        )
        assert path.name in notice, f"{path.name} no aparece en NOTICE.md (¿de dónde sale?)"
    assert (REFERENCES / "LICENSE-taste-skill").is_file()
    assert "MIT" in read(REFERENCES / "LICENSE-taste-skill")


def test_the_redesign_reference_is_the_upstream_audit() -> None:
    assert "Redesign Skill" in read(REFERENCES / "redesign.md")
    assert "redesign.md" in read(COMMANDS / "kiro-redesign.md")


# --- Type pairings ----------------------------------------------------------

_ENTRY = re.compile(
    r"^(?P<name>[A-Za-z][A-Za-z0-9 ]*?) (?P<weights>\d{3}(?:,\d{3})*)(?: (?P<kind>serif))?$"
)


def pairing_rows() -> list[dict[str, str]]:
    text = read(REFERENCES / "type-pairings.md")
    rows = []
    for line in text.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) == 6 and cells[0].isdigit():
            rows.append(
                dict(zip(("n", "style", "display", "body", "mono", "reads"), cells, strict=True))
            )
    return rows


def parse_entry(cell: str) -> tuple[str, list[int], str | None] | None:
    if cell == "-":
        return None
    match = _ENTRY.match(cell)
    assert match, f"celda de fuente ilegible: {cell!r}"
    return match["name"], [int(w) for w in match["weights"].split(",")], match["kind"]


def test_there_are_twenty_five_pairings() -> None:
    rows = pairing_rows()

    assert [int(r["n"]) for r in rows] == list(range(1, 26))


@pytest.mark.parametrize("row", pairing_rows(), ids=lambda r: f"{r['n']}-{r['display'].split()[0]}")
def test_every_pairing_is_installable_with_make_font(row: dict[str, str]) -> None:
    """Each cell must pass the same validation `make font` applies."""
    for role in ("display", "body", "mono"):
        entry = parse_entry(row[role])
        if entry is None:
            continue
        name, weights, kind = entry
        face = FontFace.model_validate({"name": name, "weights": weights, "fallback": kind})
        assert face.slug == "-".join(name.lower().split())
    assert parse_entry(row["body"]) is not None, "toda pareja necesita una fuente de texto"


def test_every_pairing_belongs_to_a_known_style() -> None:
    known = set(PRESETS)

    assert {r["style"] for r in pairing_rows()} <= known


def test_the_presets_use_families_that_the_catalogue_lists() -> None:
    """A preset must not default to a font the catalogue never vouched for."""
    listed = {
        parse_entry(r[role])[0]  # type: ignore[index]
        for r in pairing_rows()
        for role in ("display", "body", "mono")
        if parse_entry(r[role]) is not None
    }
    used = {face.name for p in PRESETS.values() for _, face in p.contract.typography.faces()}

    assert used <= listed, sorted(used - listed)


def test_fonts_that_are_not_on_fontsource_are_called_out() -> None:
    text = read(REFERENCES / "type-pairings.md")

    for name in ("Satoshi", "Cabinet Grotesk", "General Sans"):
        assert name in text
    # ...and never offered as a pairing.
    cells = " ".join(r[role] for r in pairing_rows() for role in ("display", "body", "mono"))
    assert not any(name in cells for name in ("Satoshi", "Cabinet Grotesk", "General Sans"))


# --- Commands the docs tell the AI to run -----------------------------------


def make_targets() -> set[str]:
    return set(re.findall(r"^([a-zA-Z][a-zA-Z_-]*):", read(REPO / "Makefile"), re.M))


DOCS_THAT_NAME_COMMANDS = [
    SKILL_DIR / "SKILL.md",
    REPO / "AGENTS.md",
    COMMANDS / "kiro-init.md",
    COMMANDS / "kiro-design-review.md",
    COMMANDS / "kiro-redesign.md",
    REPO / "DESIGN.md",
    REPO / "docs/getting-started.md",
    REPO / "docs/upgrading.md",
    REFERENCES / "type-pairings.md",
    REFERENCES / "archetypes.md",
    *(REFERENCES / p.reference for p in PRESETS.values() if p.reference not in VENDORED),
]


@pytest.mark.parametrize("doc", DOCS_THAT_NAME_COMMANDS, ids=lambda p: p.name)
def test_every_make_command_a_doc_names_exists(doc: Path) -> None:
    targets = make_targets()
    # A command is `make x` in backticks, or a line that starts with `make x` in a
    # code block. Prose like "make a headline" is not one.
    mentioned = set(re.findall(r"(?:`|^[ \t]*\$?[ \t]*)make ([a-z][a-z-]*)", read(doc), re.M))

    missing = mentioned - targets
    assert not missing, f"{doc.name} cita `make {sorted(missing)[0]}`, que no existe en el Makefile"


def test_the_design_subcommands_in_the_docs_are_real() -> None:
    """`make design build` works because the Makefile maps the second word."""
    makefile = read(REPO / "Makefile")
    words = re.search(r"DESIGN_WORDS := (.+)", makefile).group(1).split()  # type: ignore[union-attr]

    for word in words:
        assert f"design-{word}:" in makefile, f"`make design {word}` no tiene su objetivo"


def test_every_slash_command_a_doc_names_exists() -> None:
    commands = {p.stem for p in COMMANDS.glob("*.md")}
    skills = {p.parent.name for p in (REPO / ".claude/skills").glob("*/SKILL.md")}
    named = set()
    for doc in DOCS_THAT_NAME_COMMANDS:
        named |= set(re.findall(r"(?<![\w/.])/(kiro-[a-z-]+|spec-[a-z-]+)", read(doc)))

    assert named <= commands | skills, sorted(named - commands - skills)
    assert {"kiro-init", "kiro-design-review", "kiro-redesign"} <= commands


def test_the_commands_have_a_description_for_the_slash_menu() -> None:
    for path in COMMANDS.glob("*.md"):
        head = read(path).split("---")[1] if read(path).startswith("---") else ""
        assert "description:" in head, f"{path.name} no tiene `description` en el frontmatter"


def test_every_skill_is_named_after_its_folder() -> None:
    for path in (REPO / ".claude/skills").glob("*/SKILL.md"):
        match = re.search(r"^name: (\S+)$", read(path), re.M)
        assert match and match.group(1) == path.parent.name, path


# --- DESIGN.md --------------------------------------------------------------


def test_the_design_template_has_the_sections_the_check_looks_for() -> None:
    """Checked only while DESIGN.md is still the template.

    Once `/kiro-init` has filled it in, the project owns the file and its
    structure; the engine's own checks (`make design-check`) take over.
    """
    text = read(REPO / "DESIGN.md")
    if "TODO" not in text:
        pytest.skip("DESIGN.md ya está rellenado: es del proyecto")

    for heading in (
        "## Firma visual",
        "## Arquetipos",
        "## Los tres diales",
        "## Color",
        "## Logo",
    ):
        assert heading in text, heading
    assert "MOTION_INTENSITY" in text
    offered = re.search(r"Estilo:\*\* TODO <!-- (.+?) -->", text).group(1)  # type: ignore[union-attr]
    for name in PRESETS:
        assert name in offered


def test_agents_md_points_at_the_engine() -> None:
    text = read(REPO / "AGENTS.md")

    for needle in (
        "design.toml",
        "make design build",
        "layouts/landing.html",
        "data-motion",
        "ADR-0015",
    ):
        assert needle in text, needle


def test_the_decisions_are_indexed() -> None:
    index = read(REPO / "docs/decisions/README.md")

    for number in ("0014", "0015"):
        files = list((REPO / "docs/decisions").glob(f"{number}-*.md"))
        assert len(files) == 1
        assert files[0].name in index


# --- Archetype snippets -----------------------------------------------------


class _Balance(HTMLParser):
    """Checks that every tag a snippet opens, it closes."""

    VOID: ClassVar[set[str]] = {"img", "br", "input", "hr", "meta", "link"}

    def __init__(self) -> None:
        super().__init__()
        self.stack: list[str] = []
        self.errors: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag not in self.VOID:
            self.stack.append(tag)

    def handle_endtag(self, tag: str) -> None:
        if tag in self.VOID:
            return
        if not self.stack or self.stack[-1] != tag:
            self.errors.append(f"</{tag}> sin su apertura (abierto: {self.stack[-1:] or 'nada'})")
        else:
            self.stack.pop()


def archetype_snippets() -> list[tuple[str, str]]:
    text = read(REFERENCES / "archetypes.md")
    found = []
    for part in re.split(r"\n(?=### )", text):
        title = re.match(r"### ([^\n]+)", part)
        snippet = re.search(r"```html\n(.*?)```", part, re.S)
        if title and snippet:
            found.append((title.group(1), snippet.group(1)))
    return found


def test_the_catalogue_has_heroes_sections_and_textures() -> None:
    titles = " ".join(t for t, _ in archetype_snippets())

    for name in (
        "split",
        "type-giant",
        "bento",
        "editorial",
        "marquee",
        "sticky-stack",
        "horizontal-pan",
    ):
        assert f"`{name}`" in titles, name
    for name in (
        "statement",
        "numbered",
        "spec-sheet",
        "dark-band",
        "faq",
        "grain",
        "grid",
        "duotone",
        "mesh",
    ):
        assert f"`{name}`" in titles, name


@pytest.mark.parametrize(
    ("title", "snippet"), archetype_snippets(), ids=lambda v: v[:24] if isinstance(v, str) else ""
)
def test_an_archetype_snippet_is_well_formed_and_obeys_the_rules(title: str, snippet: str) -> None:
    parser = _Balance()
    parser.feed(snippet)

    assert parser.errors == [] and parser.stack == [], (
        f"{title}: etiquetas sin cerrar {parser.stack} {parser.errors}"
    )
    assert not re.search(r"#[0-9a-fA-F]{6}\b|#[0-9a-fA-F]{3}\b", re.sub(r"%23\w+", "", snippet)), (
        f"{title}: color escrito a mano; usa tokens"
    )
    assert "h-screen" not in snippet, f"{title}: usa min-h-[100dvh]"
    assert not re.search(r"""(src|href)=["']https?://|url\(["']?https?://""", snippet), (
        f"{title}: recurso externo (la CSP no lo carga)"
    )
    assert "Lorem" not in snippet and "John Doe" not in snippet


def test_every_motion_value_in_the_catalogue_exists_in_the_vocabulary() -> None:
    from app.design_engine.motion import VOCABULARY

    used = set(re.findall(r'data-motion="([a-z-]+)"', read(REFERENCES / "archetypes.md")))

    assert used <= set(VOCABULARY), sorted(used - set(VOCABULARY))
