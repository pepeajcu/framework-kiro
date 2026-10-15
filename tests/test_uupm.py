"""The uupm advisor: vendored intact, translated once, and safe to run.

Three layers, each tested without the network:

- the vendored tree is exactly what `vendor.lock.json` says (nobody edited it);
- `scripts/vendor_uupm.py` fetches, extracts a closed list and builds the overlay;
- `app/design_engine/advisor.py` turns uupm's JSON into a brief, for **every**
  product type uupm knows, and the result is always a valid contract.
"""

from __future__ import annotations

import csv
import io
import json
import sys
import tarfile
from collections.abc import Iterator
from pathlib import Path
from types import ModuleType

import httpx2
import pytest
from scripts import design as design_cli
from scripts import vendor_uupm as vendor

from app.branding import BrandError
from app.design_engine.advisor import (
    Overlay,
    brief_from_design_system,
    load_overlay,
)
from app.design_engine.brief import propose
from app.design_engine.checks import run_checks
from app.design_engine.contract import DesignContract, DesignError, dump_contract
from app.design_engine.design_md import read_dials
from app.design_engine.palette import derive_palette
from app.design_engine.paths import Paths
from app.design_engine.presets import PRESETS

REPO = Path(__file__).resolve().parent.parent
SKILL = REPO / ".claude/skills/kiro-design"


@pytest.fixture(scope="module")
def overlay() -> Overlay:
    return load_overlay(SKILL / "uupm-kiro")


@pytest.fixture(scope="module")
def uupm() -> Iterator[ModuleType]:
    """uupm's own engine, imported in-process from the vendored folder."""
    scripts = str(SKILL / "uupm/scripts")
    before = set(sys.modules)
    sys.path.insert(0, scripts)
    try:
        import design_system  # type: ignore[import-not-found]

        yield design_system
    finally:
        sys.path.remove(scripts)
        for name in set(sys.modules) - before:
            sys.modules.pop(name, None)


def rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


# --- What is vendored ------------


def test_the_vendored_tree_is_exactly_what_the_lock_says() -> None:
    assert vendor.verify(SKILL / "uupm") == []


def test_a_hand_edit_to_a_vendored_file_is_noticed(tmp_path: Path) -> None:
    for relative in ("scripts/core.py", "LICENSE", "vendor.lock.json"):
        (tmp_path / relative).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / relative).write_bytes((SKILL / "uupm" / relative).read_bytes())
    (tmp_path / "scripts/core.py").write_text("# editado\n")

    problems = vendor.verify(tmp_path)

    assert any("scripts/core.py no coincide" in p for p in problems)
    assert any(p.startswith("falta ") for p in problems)


def test_the_lock_names_the_pinned_commit_and_every_file_we_vendor() -> None:
    lock = json.loads((SKILL / "uupm/vendor.lock.json").read_text(encoding="utf-8"))

    assert lock["commit"] == vendor.COMMIT and lock["version"] == vendor.VERSION
    assert set(lock["files"]) == {*vendor.FILES.values(), "LICENSE"}
    assert (SKILL / "uupm/LICENSE").read_text(encoding="utf-8").startswith("MIT License")


def test_uupm_is_one_door_not_a_second_skill() -> None:
    """Its SKILL.md is saved as GUIDE.md so it cannot compete with kiro-design."""
    assert (SKILL / "uupm/GUIDE.md").is_file()
    assert not list((SKILL / "uupm").rglob("SKILL.md"))
    skills = sorted(p.parent.name for p in (REPO / ".claude/skills").glob("*/SKILL.md"))
    assert "ui-ux-pro-max" not in skills
    assert "kiro-design" in skills


def test_what_is_left_out_stays_out() -> None:
    names = {p.name for p in (SKILL / "uupm").rglob("*") if p.is_file()}

    assert not names & {
        "phosphor-icons-upstream.json",
        "google-fonts.csv",
        "google-font-licenses.json",
        "react.csv",
        "swiftui.csv",
    }
    size = sum(p.stat().st_size for p in (SKILL / "uupm").rglob("*") if p.is_file())
    assert size < 1_200_000, "uupm/ creció: ¿se coló algo que debería quedar fuera?"


# --- The vendoring script ------------


def fake_tarball() -> bytes:
    prefix = "nextlevelbuilder-ui-ux-pro-max-skill-a38d04c"
    members = {f"{vendor.UPSTREAM_SKILL}/{name}": f"contenido de {name}\n" for name in vendor.FILES}
    members[f"{vendor.UPSTREAM_SKILL}/data/google-fonts.csv"] = "Family,Category\nLora,Serif\n"
    members["LICENSE"] = "MIT License\n"
    members[f"{vendor.UPSTREAM_SKILL}/scripts/tests/test_core.py"] = "no debe venir\n"
    members["otra-cosa/README.md"] = "no debe venir\n"
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as archive:
        for name, text in members.items():
            data = text.encode()
            info = tarfile.TarInfo(f"{prefix}/{name}")
            info.size = len(data)
            archive.addfile(info, io.BytesIO(data))
    return buffer.getvalue()


def test_extraction_takes_the_closed_list_and_nothing_else() -> None:
    found = vendor.extract(fake_tarball())

    assert set(found) == {*vendor.FILES, "LICENSE", "google-fonts.csv"}
    assert not any("tests" in name for name in found)


def test_a_tarball_that_lacks_a_file_we_need_is_refused() -> None:
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as archive:
        info = tarfile.TarInfo("x-y/LICENSE")
        info.size = 0
        archive.addfile(info, io.BytesIO(b""))

    with pytest.raises(BrandError, match="no trae"):
        vendor.extract(buffer.getvalue())


def test_vendoring_renames_the_skill_to_a_guide_and_writes_a_matching_lock(tmp_path: Path) -> None:
    vendor.write_vendored(vendor.extract(fake_tarball()), tmp_path)

    assert (tmp_path / "GUIDE.md").is_file() and not (tmp_path / "SKILL.md").exists()
    assert vendor.verify(tmp_path) == []
    lock = json.loads((tmp_path / "vendor.lock.json").read_text(encoding="utf-8"))
    assert lock["files"]["GUIDE.md"] == vendor.sha256(b"contenido de SKILL.md\n")


def test_the_whole_run_with_a_simulated_network(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fontsource = [
        {"family": "Lora", "subsets": ["latin"], "weights": [400, 700], "category": "serif"}
    ]

    def handler(request: httpx2.Request) -> httpx2.Response:
        url = str(request.url)
        if url == vendor.TARBALL_URL:
            return httpx2.Response(200, content=fake_tarball())
        if url == vendor.FONTSOURCE_URL:
            return httpx2.Response(200, content=json.dumps(fontsource).encode())
        return httpx2.Response(404)

    # The fake files are not real CSV: the overlay has its own tests below.
    monkeypatch.setattr(vendor, "write_overlay", lambda files, fonts, dest: {"fonts.csv": 0})
    messages: list[str] = []

    vendor.run(
        root=tmp_path,
        client=httpx2.Client(transport=httpx2.MockTransport(handler)),
        log=messages.append,
    )

    assert (tmp_path / ".claude/skills/kiro-design/uupm/GUIDE.md").is_file()
    assert any("archivos escritos" in m for m in messages)


# --- Building the overlay ------------


FONTSOURCE = [
    {"family": "Lora", "subsets": ["latin"], "weights": [400, 500, 700], "category": "serif"},
    {
        "family": "Inter",
        "subsets": ["latin", "greek"],
        "weights": [400, 600],
        "category": "sans-serif",
    },
    {"family": "Courier Prime", "subsets": ["latin"], "weights": [400], "category": "monospace"},
    {
        "family": "Only Cyrillic",
        "subsets": ["cyrillic"],
        "weights": [400],
        "category": "sans-serif",
    },
    {"family": "Only Bold", "subsets": ["latin"], "weights": [700], "category": "sans-serif"},
]


def test_fonts_are_matched_by_family_and_fall_back_to_a_category() -> None:
    typography = (
        b"Heading Font,Body Font\nLora,Inter\nCourier Prime,Only Cyrillic\nMissing Font,Only Bold\n"
    )
    google = b"Family,Category\nMissing Font,Monospace\nOnly Bold,Sans Serif\n"

    table = {r["source_font"]: r for r in vendor.build_fonts(typography, google, FONTSOURCE)}

    assert table["Lora"] == {
        "source_font": "Lora",
        "fontsource": "Lora",
        "category": "serif",
        "weights": "400 500 700",
    }
    assert table["Courier Prime"]["category"] == "mono"
    # No latin subset, or no regular weight: not installable, so no Fontsource family.
    assert table["Only Cyrillic"]["fontsource"] == ""
    assert table["Only Bold"]["fontsource"] == ""
    assert table["Missing Font"] == {
        "source_font": "Missing Font",
        "fontsource": "",
        "category": "mono",
        "weights": "",
    }


def test_palettes_say_whether_the_primary_passes_and_what_taste_would_flag() -> None:
    colors = (
        b"Product Type,Primary\n"
        b"Reads,#0F766E\nFails,#0080A0\nPurple,#7C3AED\nNeon,#00FF55\nBroken,not-a-colour\n"
    )

    table = {r["product_type"]: r for r in vendor.build_palettes(colors)}

    assert table["Reads"]["aa"] == "ok" and table["Reads"]["suggested"] == ""
    assert table["Fails"]["aa"] == "fails" and table["Fails"]["suggested"].startswith("#")
    assert table["Purple"]["purple"] == "yes"
    assert table["Neon"]["saturated"] == "yes"
    assert table["Broken"]["aa"] == "invalid"


@pytest.mark.parametrize(
    ("text", "preset"),
    [
        ("Neo-Brutalism", "neo-brutalista"),
        ("Swiss Brutalist", "brutalista"),
        ("Retro Y2K", "retro-y2k"),
        ("Terminal / Hacker", "oscuro-tecnologico"),
        ("Editorial Magazine", "editorial"),
        ("Organic Biophilic", "organico"),
        ("Dashboard Analytics", "panel-de-datos"),
        ("Corporate Enterprise", "institucional"),
        ("Soft UI Evolution", "suave-premium"),
        ("Vibrant Gradient", "expresivo"),
        ("Minimalism", "minimalista"),
        ("Something Unnamed", ""),
    ],
)
def test_a_style_maps_to_the_nearest_preset_by_what_it_is_called(text: str, preset: str) -> None:
    assert vendor.nearest_preset(text) == preset


def test_the_mapping_only_names_presets_that_exist() -> None:
    assert {preset for _, preset in vendor.STYLE_RULES} <= set(PRESETS)
    assert vendor.nearest_preset("Minimalism", presets=["editorial"]) == ""


def test_a_style_is_named_by_its_title_first_and_best_for_is_ignored() -> None:
    styles = (
        b"Style ID,Style Category,Keywords,Aliases,Best For\n"
        b"soft-ui,Soft UI Evolution,modern,,Modern enterprise apps and corporate tools\n"
    )

    (row,) = vendor.build_styles(styles)

    assert row["preset"] == "suave-premium"


def test_stack_advice_that_cannot_be_followed_here_is_listed_with_its_reason() -> None:
    stack = (
        b"No,Guideline,Do\n"
        b'1,Load Tailwind,<script src="https://cdn.tailwindcss.com"></script>\n'
        b"2,Build,run npm install and postcss\n"
        b"3,Fonts,@import fonts.googleapis.com\n"
        b"4,Spacing,use gap-4\n"
    )

    skipped = {r["no"]: r["reason"] for r in vendor.build_stack_skips(stack)}

    assert set(skipped) == {"1", "2", "3"}
    assert "CDN" in skipped["1"] and "Node" in skipped["2"] and "fuente" in skipped["3"]


# --- The committed overlay agrees with the data and with Kiro ------------


def test_the_overlay_covers_every_font_palette_and_style_uupm_has() -> None:
    data = SKILL / "uupm/data"
    fonts = {r["source_font"] for r in rows(SKILL / "uupm-kiro/fonts.csv")}
    named = {
        r[key].strip()
        for r in rows(data / "typography.csv")
        for key in ("Heading Font", "Body Font")
    }
    palettes = {r["product_type"] for r in rows(SKILL / "uupm-kiro/palettes.csv")}
    styles = {r["style_id"] for r in rows(SKILL / "uupm-kiro/styles.csv")}

    assert named <= fonts
    assert palettes == {r["Product Type"].strip() for r in rows(data / "colors.csv")}
    assert len(styles) == len(rows(data / "styles.csv"))


def test_every_font_the_overlay_vouches_for_can_be_installed_by_make_font() -> None:
    from app.design_engine.contract import FontFace

    for row in rows(SKILL / "uupm-kiro/fonts.csv"):
        assert row["category"] in {"sans", "serif", "mono"}, row
        if row["fontsource"]:
            weights = [int(w) for w in row["weights"].split()]
            assert 400 in weights, row
            FontFace.model_validate({"name": row["fontsource"], "weights": [400]})


def test_the_palette_verdicts_still_agree_with_the_compiler() -> None:
    """If the compiler changes what passes AA, the overlay must be rebuilt."""
    from app.design_engine.contract import Brand

    for row in rows(SKILL / "uupm-kiro/palettes.csv"):
        if row["aa"] == "invalid":
            continue
        passes = not derive_palette(Brand.model_validate({"primary": row["primary"]})).failures
        assert passes == (row["aa"] == "ok"), row["product_type"]
        if not passes:
            assert row["suggested"], row["product_type"]


def test_the_overlay_only_names_presets_that_exist() -> None:
    used = {r["preset"] for r in rows(SKILL / "uupm-kiro/styles.csv") if r["preset"]}

    assert used <= set(PRESETS)
    assert len(used) >= 8, "casi ningún estilo de uupm tiene preset: las reglas se rompieron"


# --- Turning uupm's answer into a proposal ------------


def system(**overrides: object) -> dict[str, object]:
    design: dict[str, object] = {
        "category": "Beauty/Spa/Wellness Service",
        "pattern": {
            "name": "Hero + Testimonials + CTA",
            "sections": "Hero > Testimonials carousel > CTA",
            "conversion": "Social proof before CTA",
        },
        "style": {
            "id": "soft-ui-evolution",
            "name": "Soft UI Evolution",
            "keywords": "evolved soft ui, better contrast, subtle depth",
            "accessibility": "risk:low",
        },
        "colors": {
            "primary": "#0F766E",
            "secondary": "#F9A8D4",
            "accent": "#8B5CF6",
            "background": "#FDF2F8",
            "muted_foreground": "#475569",
        },
        "typography": {
            "heading": "Lora",
            "body": "Raleway",
            "google_fonts_url": "https://fonts.googleapis.com/css2?family=Lora:wght@400;700",
        },
        "anti_patterns": "Bright neon colors + Harsh animations",
        "constraints": ["booking-system"],
    }
    design.update(overrides)
    return {"design_system": design}


def test_the_advice_becomes_a_base_brief_with_its_provenance(overlay: Overlay) -> None:
    advice = brief_from_design_system(system(), overlay, dials={"motion": 4})

    brief = advice.brief
    assert brief.source == "advisor" and advice.preset == "suave-premium"
    assert "uupm v2.15.0" in brief.provenance and "Soft UI Evolution" in brief.provenance
    assert (brief.theme, brief.header) == ("luma", "floating-pill")
    assert brief.motion == 4  # the project's own dial beats the preset's
    assert [c.role for c in brief.colours] == ["primary", "secondary", "accent"]
    assert brief.anti_patterns == ("Bright neon colors", "Harsh animations")
    assert any("booking-system" in note for note in brief.ux_notes)


def test_a_carousel_is_flagged_for_the_review_not_decided_here(overlay: Overlay) -> None:
    notes = brief_from_design_system(system(), overlay).brief.ux_notes

    assert any("carrusel" in n and "P3" in n for n in notes)


def test_fonts_keep_their_category_and_only_weights_fontsource_has(overlay: Overlay) -> None:
    advice = brief_from_design_system(system(), overlay)

    by_role = {f.role: f for f in advice.brief.fonts}
    assert by_role["display"].name == "Lora" and by_role["display"].category == "serif"
    assert set(by_role["display"].weights) <= {400, 500, 600, 700}
    assert advice.fonts["lora"] == "Lora"


@pytest.mark.parametrize(
    ("background", "surface"),
    [("#0B0F14", "dark"), ("#FFFFFF", "light"), ("#FAF6EE", "cream")],
)
def test_the_surface_is_read_from_the_background(
    overlay: Overlay, background: str, surface: str
) -> None:
    colours = {"primary": "#0F766E", "background": background, "muted_foreground": "#475569"}

    assert brief_from_design_system(system(colors=colours), overlay).brief.surface == surface


def test_a_response_without_a_design_system_is_an_error_not_a_crash(overlay: Overlay) -> None:
    with pytest.raises(DesignError, match="design_system"):
        brief_from_design_system({"nada": 1}, overlay)


def test_every_product_type_uupm_knows_gives_a_valid_contract(
    uupm: ModuleType, overlay: Overlay
) -> None:
    """The exhaustive test: 192 product types, each through uupm's own engine."""
    failures: list[str] = []
    types = [r["product_type"] for r in rows(SKILL / "uupm-kiro/palettes.csv")]
    assert len(types) >= 150

    for product in types:
        result = uupm.generate_design_system(product, "Test")  # type: ignore[attr-defined]
        advice = brief_from_design_system({"design_system": result["design_system"]}, overlay)
        proposal = propose(base=advice.brief, current=DesignContract(), fonts=advice.fonts)
        contract = proposal.contract
        try:
            assert not derive_palette(contract.brand).failures
            assert contract == type(contract).model_validate_json(contract.model_dump_json())
            assert contract.typography.display or contract.typography.body
        except AssertionError:
            failures.append(product)
        if proposal.unresolved:
            failures.append(f"{product}: {proposal.unresolved}")

    assert not failures, failures


# --- The command ------------


@pytest.fixture
def project_with_uupm(tmp_path: Path) -> Paths:
    """A project slice that has the vendored advisor and its overlay."""
    import shutil

    paths = Paths(tmp_path)
    shutil.copytree(SKILL / "uupm", paths.uupm)
    shutil.copytree(SKILL / "uupm-kiro", paths.uupm_overlay)
    paths.contract.write_text(dump_contract(DesignContract()), encoding="utf-8")
    return paths


def test_advise_runs_uupm_isolated_and_saves_a_reviewable_proposal(
    project_with_uupm: Paths,
) -> None:
    paths = project_with_uupm
    paths.design_md.write_text(
        "| `DESIGN_VARIANCE` | 7 | x | y |\n| `MOTION_INTENSITY` | 4 | x | y |\n"
        "| `VISUAL_DENSITY` | 3 | x | y |\n",
        encoding="utf-8",
    )

    slug, proposal = design_cli.advise(paths, "luxury spa wellness booking", name="spa")

    assert slug == "spa"
    for relative in ("uupm/spa.json", "briefs/spa.json", "proposals/spa.json", "proposals/spa.md"):
        assert (paths.work / relative).is_file(), relative
    assert proposal.contract.motion.level == 4
    assert "uupm" in proposal.provenance[0]
    # Nothing outside .design/ was written: uupm's own persistence is never used.
    assert not (paths.root / "design-system").exists()
    assert load_contract_is_default(paths)


def load_contract_is_default(paths: Paths) -> bool:
    from app.design_engine.contract import load_contract

    return load_contract(paths.contract).is_default


def test_ux_search_answers_in_text_and_rejects_an_unknown_domain(project_with_uupm: Paths) -> None:
    text = design_cli.search_ux(project_with_uupm, "form validation", domain="ux", stack=False)
    stack = design_cli.search_ux(project_with_uupm, "animation", domain="ux", stack=True)

    assert text.strip() and stack.strip()
    with pytest.raises(DesignError, match="no válido"):
        design_cli.search_ux(project_with_uupm, "x", domain="icons", stack=False)


def test_without_the_advisor_the_command_says_how_to_get_it(tmp_path: Path) -> None:
    with pytest.raises(DesignError, match="vendor_uupm"):
        design_cli.advise(Paths(tmp_path), "spa", name=None)


def test_the_dials_are_read_from_design_md_and_a_todo_is_ignored() -> None:
    filled = "| `DESIGN_VARIANCE` | 7 | a | b |\n| `MOTION_INTENSITY` | 10 | a | b |\n"
    todo = "| `DESIGN_VARIANCE` | TODO | a | b |\n| `VISUAL_DENSITY` | 11 | a | b |\n"

    assert read_dials(filled) == {"variance": 7, "motion": 10}
    assert read_dials(todo) == {}


# --- design-check watches for a rival ------------


def test_a_competing_design_skill_is_reported(project_with_uupm: Paths) -> None:
    paths = project_with_uupm
    rival = paths.skill.parent / "ui-ux-pro-max"
    rival.mkdir(parents=True)
    (rival / "SKILL.md").write_text("---\nname: ui-ux-pro-max\n---\n", encoding="utf-8")

    findings = run_checks(paths, allow_defaults=True)

    hit = [f for f in findings if "compite con kiro-design" in f.message]
    assert len(hit) == 1 and hit[0].level == "warn" and "ui-ux-pro-max" in hit[0].message


def test_without_rivals_nothing_is_said(project_with_uupm: Paths) -> None:
    findings = run_checks(project_with_uupm, allow_defaults=True)

    assert not [f for f in findings if "compite" in f.message]
