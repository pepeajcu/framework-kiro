"""One pipeline from any design source to the contract.

Rules and generic patterns, `DesignBrief` and `propose`, writing into
`DESIGN.md`, and the `propose` / `apply` commands. Same conventions as the
other design tests: a temporary project, no network.
"""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

import pytest
from scripts import design as design_cli

from app.design_engine import patterns
from app.design_engine.brief import (
    BriefColour,
    BriefFont,
    DesignBrief,
    decision_lines,
    proposal_from_data,
    proposal_to_data,
    propose,
    provenance_entry,
    render_report,
    theme_for,
)
from app.design_engine.checks import run_checks
from app.design_engine.contract import (
    DesignContract,
    DesignError,
    dump_contract,
    load_contract,
    parse_contract,
)
from app.design_engine.design_md import DECISIONS_HEADING, PROVENANCE_HEADING, add_lines
from app.design_engine.paths import Paths
from app.design_engine.presets import PRESETS
from app.design_engine.rules import CATEGORIES, FLOOR, GENERIC_PATTERNS, RELAXABLE, RULES
from tests.test_design_scripts import set_contract

TODAY = dt.date(2026, 10, 14)


def brief(**overrides: object) -> DesignBrief:
    data: dict[str, object] = {"source": "reference", "provenance": "https://ejemplo.test/web"}
    data.update(overrides)
    return DesignBrief.model_validate(data)


# --- The rule table -----------------------------------------------------------


def test_the_floor_is_the_first_three_categories_and_cannot_be_relaxed() -> None:
    assert {1, 2, 3} == FLOOR
    assert not any(RULES[r].relaxable for r in RULES if RULES[r].category in FLOOR)
    assert set(RELAXABLE) == {r for r in RULES if RULES[r].category not in FLOOR}
    assert set(GENERIC_PATTERNS) == {f"P{n}" for n in range(1, 11)}


def test_every_rule_has_a_category_a_title_and_a_fix() -> None:
    for rule in RULES.values():
        assert rule.category in CATEGORIES, rule.id
        assert rule.title and rule.fix, rule.id


# --- `[rules]` in the contract ------------------------------------------------------


def test_allow_is_normalised_sorted_and_deduplicated() -> None:
    contract = parse_contract('[rules]\nallow = ["p2", "P1", "P2"]\n')

    assert contract.rules.allow == ("P1", "P2")
    assert not contract.is_default


@pytest.mark.parametrize("bad", ['["D1"]', '["D2"]', '["ZZ"]', '"P1"'])
def test_allow_rejects_the_floor_unknown_ids_and_non_lists(bad: str) -> None:
    with pytest.raises(DesignError, match=r"rules\.allow"):
        parse_contract(f"[rules]\nallow = {bad}\n")


def test_the_toml_only_mentions_rules_when_a_rule_is_allowed() -> None:
    assert "[rules]" not in dump_contract(DesignContract())

    contract = parse_contract('[rules]\nallow = ["P1"]\n')
    dumped = dump_contract(contract)

    assert '[rules]\nallow = ["P1"]' in dumped
    assert parse_contract(dumped) == contract


def test_design_set_writes_and_clears_the_allowed_rules(project: Paths) -> None:
    design_cli.set_values(project, ["rules.allow=p1, P3"])
    assert load_contract(project.contract).rules.allow == ("P1", "P3")

    design_cli.set_values(project, ["rules.allow="])
    assert load_contract(project.contract).rules.allow == ()

    with pytest.raises(DesignError, match="no se puede permitir"):
        design_cli.set_values(project, ["rules.allow=D1"])


def test_estandar_shadcn_is_the_default_look_chosen_on_purpose() -> None:
    contract = PRESETS["estandar-shadcn"].contract

    assert not contract.is_default
    assert contract.rules.allow == tuple(sorted(GENERIC_PATTERNS))
    assert contract.brand == DesignContract().brand
    assert contract.basecoat == DesignContract().basecoat


# --- Generic patterns ----------------------------------------------------------------

THREE_CARDS = (
    '<section class="text-center"><h1>Titulo</h1></section>'
    '<div class="grid md:grid-cols-3">'
    '<div class="card">a</div><div class="card">b</div><div class="card">c</div></div>'
)


def rules_of(markup: str) -> list[str]:
    return [hit.rule for hit in patterns.scan(patterns.strip_comments(markup))]


@pytest.mark.parametrize(
    ("rule", "markup"),
    [
        ("P1", THREE_CARDS),
        ("P2", "<p>Empresas que confían en nosotros</p>"),
        ("P2", "<p>Trusted by teams</p>"),
        ("P3", '<div class="testimonials carousel"></div>'),
        (
            "P4",
            "<h2>Precios</h2>"
            '<div class="grid grid-cols-3">'
            '<div class="card">$9 /mes</div><div class="card">$19 /mes</div>'
            '<div class="card">$29 /mes</div></div>',
        ),
        ("P5", '<div class="h-screen"></div>'),
        ("P5", '<div class="md:h-screen"></div>'),
        ("P6", '<div class="backdrop-blur"><p>contenido</p></div>'),
        ("P7", "<p>Listo 🚀</p>"),
        ("P8", "<h1>Elevate your workflow</h1>"),
        ("P8", "<p>A seamless experience</p>"),
        ("P9", "<p>Una frase — otra frase</p>"),
        ("P9", "<p>Una frase &mdash; otra</p>"),
        ("P10", "<p>Hecho por John Doe</p>"),
        ("P10", "<p>Lorem ipsum dolor</p>"),
    ],
)
def test_a_generic_pattern_is_found(rule: str, markup: str) -> None:
    assert rule in rules_of(markup)


@pytest.mark.parametrize(
    "markup",
    [
        # Not centred, or fewer than three cards, or no grid of three.
        '<h1 class="text-left">T</h1><div class="grid grid-cols-3"><div class="card">a</div></div>',
        '<section class="text-center"><h1>T</h1></section><ul class="divide-y"><li>a</li></ul>',
        # Blur on, or inside, a fixed or sticky bar.
        '<header class="sticky top-0"><nav class="backdrop-blur">x</nav></header>',
        '<div class="fixed inset-x-0 backdrop-blur">x</div>',
        '<div class="md:sticky backdrop-blur">x</div>',
        # Documented in a comment, not used.
        "{# h-screen, Elevate, 🚀, John Doe, — #}",
        "<!-- confían en nosotros -->",
        # Metadata is not copy; code is not text.
        "{% block title %}Sin permiso — Mi sitio{% endblock %}",
        "<script>const x = 'Elevate — 🚀'</script>",
        # Tokens, SVG, real copy.
        '<div class="min-h-[100dvh] bg-primary"></div>',
        "<p>El dominio real, con comas, y dos frases.</p>",
        "<p>Un texto sin nada raro</p>",
    ],
)
def test_ordinary_markup_is_left_alone(markup: str) -> None:
    assert rules_of(markup) == []


def test_pattern_findings_name_the_file_the_rule_and_how_to_allow_it(
    project: Paths,
) -> None:
    page = project.templates / "pages" / "home.html"
    page.parent.mkdir(parents=True)
    page.write_text(THREE_CARDS + "<div class='h-screen'></div>", encoding="utf-8")

    findings = run_checks(project, allow_defaults=True)

    found = [f for f in findings if f.message.startswith("P")]
    assert {f.message.split()[0] for f in found} == {"P1", "P5"}
    assert all("pages/home.html" in f.message and f.level == "warn" for f in found)
    assert 'allow = ["P1"]' in next(f.hint or "" for f in found if f.message.startswith("P1"))


def test_an_allowed_pattern_is_silent_but_the_allowance_is_always_reported(
    project: Paths,
) -> None:
    page = project.templates / "pages" / "home.html"
    page.parent.mkdir(parents=True)
    page.write_text(THREE_CARDS, encoding="utf-8")
    set_contract(project, parse_contract('[rules]\nallow = ["P1"]\n'))
    design_cli.build(project)

    findings = run_checks(project, allow_defaults=False)

    assert not any(f.message.startswith("P1 ") for f in findings)
    allowance = [f for f in findings if "permite patrones genéricos" in f.message]
    assert len(allowance) == 1 and allowance[0].level == "warn"
    assert "P1" in allowance[0].message
    # Choosing the generic look on purpose is a choice: no "still the defaults" error.
    assert not any(f.level == "error" for f in findings)


def test_the_estandar_shadcn_preset_silences_every_generic_pattern(
    project: Paths,
) -> None:
    page = project.templates / "pages" / "home.html"
    page.parent.mkdir(parents=True)
    page.write_text(THREE_CARDS + "<p>Elevate — 🚀 John Doe</p>", encoding="utf-8")
    set_contract(project, PRESETS["estandar-shadcn"].contract)

    findings = run_checks(project, allow_defaults=False)

    assert not [f for f in findings if f.message[:1] == "P" and f.message[1:2].isdigit()]


def test_the_frameworks_own_templates_are_free_of_generic_patterns() -> None:
    findings = run_checks(Paths(), allow_defaults=True)

    assert [f.message for f in findings if f.message[:1] == "P" and f.message[1:2].isdigit()] == []


# --- propose ---------------------------------------------------------------------------------


def test_nothing_to_propose_keeps_the_contract_and_says_so() -> None:
    proposal = propose(current=PRESETS["editorial"].contract)

    assert proposal.contract == PRESETS["editorial"].contract
    assert proposal.notes


def test_one_accent_is_kept_and_the_others_are_written_down() -> None:
    source = brief(
        colours=[
            {"hex": "#FFFFFF", "role": "background", "weight": 0.6},
            {"hex": "#0F766E", "weight": 0.2},
            {"hex": "#DC2626", "weight": 0.05},
            {"hex": "#222222", "role": "text", "weight": 0.1},
        ]
    )

    proposal = propose(inspiration=source)

    assert proposal.contract.brand.primary == "#0F766E"
    assert any("#DC2626" in note and "descartados" in note for note in proposal.notes)


def test_a_role_beats_usage_when_choosing_the_accent() -> None:
    source = brief(
        colours=[
            {"hex": "#DC2626", "weight": 0.9},
            {"hex": "#2563EB", "role": "primary", "weight": 0.01},
        ]
    )

    assert propose(inspiration=source).contract.brand.primary == "#2563EB"


def test_a_secondary_colour_is_kept_when_the_source_names_one() -> None:
    source = brief(
        colours=[
            {"hex": "#0F766E", "role": "primary"},
            {"hex": "#B45309", "role": "secondary"},
        ]
    )

    brand = propose(inspiration=source).contract.brand
    assert (brand.primary, brand.secondary) == ("#0F766E", "#B45309")


def test_a_colour_that_cannot_carry_a_button_moves_to_the_nearest_that_can() -> None:
    proposal = propose(inspiration=brief(colours=[{"hex": "#0080A0", "role": "primary"}]))

    (decision,) = proposal.decisions
    assert (decision.field, decision.before, decision.rule) == ("brand.primary", "#0080A0", "D1")
    assert proposal.contract.brand.primary == decision.after != "#0080A0"
    assert proposal.unresolved == ()


def test_the_secondary_is_checked_against_the_primary_as_it_ended_up() -> None:
    """A primary that had to move must not make a perfectly good secondary look bad."""
    source = brief(
        colours=[
            {"hex": "#6366F1", "role": "primary"},
            {"hex": "#818CF8", "role": "secondary"},
        ]
    )

    proposal = propose(inspiration=source)

    assert proposal.unresolved == ()
    assert [d.field for d in proposal.decisions] == ["brand.primary"]
    assert proposal.contract.brand.secondary == "#818CF8"


def test_a_source_with_only_neutrals_leaves_the_accent_to_a_person() -> None:
    source = brief(colours=[{"hex": "#FFFFFF", "weight": 0.7}, {"hex": "#111111", "weight": 0.3}])

    proposal = propose(inspiration=source, current=PRESETS["editorial"].contract)

    assert proposal.contract.brand.primary == PRESETS["editorial"].contract.brand.primary
    assert any("acento" in item for item in proposal.unresolved)


def test_fonts_use_the_vouched_table_then_the_catalogue_then_the_category() -> None:
    source = brief(
        fonts=[
            {"name": "SF Pro Display", "role": "display", "category": "sans", "weights": [600]},
            {"name": "Fraunces", "role": "body", "category": "serif"},
            {"name": "Obscure Slab", "role": "mono", "category": "mono"},
        ]
    )

    proposal = propose(inspiration=source, fonts={"sf pro display": "Inter"})

    typography = proposal.contract.typography
    assert typography.display is not None and typography.display.name == "Inter"
    assert typography.display.weights == (600,)
    assert typography.body is not None and typography.body.name == "Fraunces"
    assert typography.body.fallback == "serif"
    assert typography.mono is not None and typography.mono.name == "JetBrains Mono"
    changed = {d.field: d for d in proposal.decisions}
    assert "equivalente en Fontsource" in changed["type.display"].reason
    assert "categoría mono" in changed["type.mono"].reason
    assert "type.body" not in changed


@pytest.mark.parametrize(
    ("radius", "expected"),
    [("12px", "0.75rem"), ("0.5rem", "0.5rem"), ("0", "0rem"), ("40px", "2rem")],
)
def test_the_radius_becomes_rem_and_is_capped(radius: str, expected: str) -> None:
    assert propose(inspiration=brief(radius=radius)).contract.brand.radius == expected


def test_a_radius_that_is_not_a_length_is_unresolved_not_a_crash() -> None:
    proposal = propose(inspiration=brief(radius="muy redondo"))

    assert any("muy redondo" in item for item in proposal.unresolved)
    assert proposal.contract.brand.radius == DesignContract().brand.radius


@pytest.mark.parametrize(
    ("rem", "density", "theme"),
    [
        (0, 5, "lyra"),
        (0.25, 3, "vega"),
        (0.25, 8, "mira"),
        (0.5, 5, "nova"),
        (0.75, 5, "maia"),
        (1.25, 5, "luma"),
        (1.5, 5, "rhea"),
    ],
)
def test_the_theme_follows_the_radius_and_the_density(rem: float, density: int, theme: str) -> None:
    assert theme_for(rem, density) == theme


def test_a_derived_theme_is_recorded_and_a_named_one_is_not_second_guessed() -> None:
    derived = propose(inspiration=brief(radius="0px", density=5))
    named = propose(inspiration=brief(radius="0px", theme="rhea"))

    assert derived.contract.basecoat.theme == "lyra"
    assert any(d.field == "basecoat.theme" for d in derived.decisions)
    assert named.contract.basecoat.theme == "rhea"
    assert not any(d.field == "basecoat.theme" for d in named.decisions)


def test_the_inspiration_wears_the_baseline_it_does_not_replace_it() -> None:
    baseline = brief(
        source="advisor",
        provenance="uupm: spa",
        colours=[{"hex": "#0F766E", "role": "primary"}],
        surface="cream",
        ux_notes=["estados de carga con esqueleto"],
        keywords=["calma"],
    )
    inspiration = brief(
        provenance="https://ejemplo.test",
        radius="16px",
        header="floating-pill",
        motion=6,
        ux_notes=["estados de carga con esqueleto", "foco visible"],
    )

    proposal = propose(base=baseline, inspiration=inspiration)

    contract = proposal.contract
    assert contract.brand.primary == "#0F766E"
    assert contract.brand.surface == "cream"
    assert contract.brand.radius == "1rem"
    assert (contract.structure.header, contract.motion.level) == ("floating-pill", 6)
    assert proposal.ux_notes == ("estados de carga con esqueleto", "foco visible")
    assert proposal.provenance == ("uupm: spa", "https://ejemplo.test")
    assert proposal.inputs == ("advisor", "reference")


def test_what_the_briefs_leave_open_stays_and_allowed_rules_are_kept() -> None:
    current = parse_contract('[brand]\nprimary = "#7F1D1D"\n[rules]\nallow = ["P2"]\n')

    proposal = propose(inspiration=brief(radius="8px"), current=current)

    assert proposal.contract.brand.primary == "#7F1D1D"
    assert proposal.contract.brand.radius == "0.5rem"
    assert proposal.contract.rules.allow == ("P2",)


def test_a_proposal_always_makes_a_valid_contract() -> None:
    hostile = brief(
        colours=[{"hex": "#123456", "role": "primary"}],
        fonts=[{"name": "<script>", "role": "body"}],
        radius="3px",
        density=10,
        motion=10,
    )

    proposal = propose(inspiration=hostile)

    assert proposal.contract.typography.body is not None
    assert proposal.contract.typography.body.name == "Public Sans"
    assert proposal.contract == parse_contract(dump_contract(proposal.contract))


def test_a_brief_rejects_what_cannot_be_a_colour_or_a_dial() -> None:
    with pytest.raises(ValueError, match="hex"):
        BriefColour(hex="rojo")
    with pytest.raises(ValueError, match="less than or equal"):
        brief(motion=11)
    with pytest.raises(ValueError, match="Extra inputs"):
        brief(unknown=1)
    assert BriefFont(name="Inter", role="body").weights == (400,)


# --- Saving and reporting ---------------------------------------------------------------------


def test_a_proposal_survives_a_round_trip_through_json() -> None:
    original = propose(
        inspiration=brief(colours=[{"hex": "#0080A0", "role": "primary"}], radius="12px")
    )

    data = json.loads(json.dumps(proposal_to_data(original, TODAY)))

    assert proposal_from_data(data) == original


@pytest.mark.parametrize(
    ("patch", "message"),
    [
        ({"version": 99}, "otra versión"),
        ({"contract": None}, "contrato"),
        ({"contract": {"brand": {"primary": "no"}}}, "design.toml tiene"),
        ({"decisions": "x"}, "decisions"),
        ({"notes": [1]}, "notes"),
        ({"inputs": ["magia"]}, "fuentes desconocidas"),
    ],
)
def test_an_edited_proposal_is_validated_not_trusted(
    patch: dict[str, object], message: str
) -> None:
    data = proposal_to_data(propose(inspiration=brief(radius="8px")), TODAY)
    data.update(patch)

    with pytest.raises(DesignError, match=message):
        proposal_from_data(data)


def test_the_report_lists_changes_decisions_and_what_is_open() -> None:
    current = DesignContract()
    proposal = propose(
        inspiration=brief(
            colours=[{"hex": "#0080A0", "role": "primary"}, {"hex": "#DC2626"}],
            radius="muy redondo",
            ux_notes=["foco visible"],
            anti_patterns=["tres tarjetas iguales"],
        ),
        current=current,
    )

    report = render_report(proposal, current, TODAY)

    assert "| `brand.primary` |" in report
    assert "[D1]" in report
    assert "Sin resolver" in report and "muy redondo" in report
    assert "foco visible" in report and "tres tarjetas iguales" in report
    assert "make design-apply" in report


def test_design_md_lines_carry_the_date_the_rule_and_the_reason() -> None:
    proposal = propose(inspiration=brief(colours=[{"hex": "#0080A0", "role": "primary"}]))

    lines = decision_lines(proposal, TODAY)
    entry = provenance_entry(proposal, TODAY)

    assert lines[0].startswith("- 2026-10-14 · `brand.primary` [D1]:")
    assert "reference" in entry and "https://ejemplo.test/web" in entry
    assert "ni logos, ni imágenes" in entry


# --- DESIGN.md --------------------------------------------------------------------------------


def test_lines_are_added_to_the_end_of_their_section_and_nothing_else_moves() -> None:
    text = (
        f"# D\n\n{DECISIONS_HEADING}\n\n<!-- nota -->\n\n"
        f"{PROVENANCE_HEADING}\n\n- a\n\n## Logo\n\nx\n"
    )

    out = add_lines(text, PROVENANCE_HEADING, ["- b"])
    out = add_lines(out, DECISIONS_HEADING, ["- uno"])

    assert "- a\n- b\n\n## Logo" in out
    assert "<!-- nota -->\n\n- uno\n\n## Procedencia" in out
    assert out.endswith("## Logo\n\nx\n")


def test_adding_the_same_line_twice_changes_nothing() -> None:
    once = add_lines("# D\n", PROVENANCE_HEADING, ["- z"])

    assert add_lines(once, PROVENANCE_HEADING, ["- z"]) == once
    assert add_lines(once, PROVENANCE_HEADING, []) == once


def test_a_missing_section_is_created_at_the_end() -> None:
    out = add_lines("# D\n\n## Logo\n\nx\n", DECISIONS_HEADING, ["- uno"])

    assert out.endswith("x\n\n## Decisiones de diseño\n\n- uno\n")


# --- The commands ---------------------------------------------------------------------------------


def write_brief(path: Path, **overrides: object) -> Path:
    data: dict[str, object] = {
        "source": "reference",
        "provenance": "https://ejemplo.test/web",
        "title": "Web de ejemplo",
        "colours": [{"hex": "#0080A0", "role": "primary"}],
        "radius": "12px",
        "motion": 5,
    }
    data.update(overrides)
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def test_propose_writes_the_three_files_and_touches_nothing_else(
    project: Paths,
    tmp_path: Path,
) -> None:
    before = project.contract.read_text(encoding="utf-8")
    source = write_brief(tmp_path / "brief.json")

    slug, proposal = design_cli.make_proposal(
        project, source=source, base=None, name=None, today=TODAY
    )

    assert slug == "web-de-ejemplo"
    for suffix in ("json", "toml", "md"):
        assert (project.proposals / f"{slug}.{suffix}").is_file()
    assert (
        parse_contract((project.proposals / f"{slug}.toml").read_text("utf-8")) == proposal.contract
    )
    assert project.contract.read_text(encoding="utf-8") == before
    assert not project.design_md.exists()


def test_propose_needs_a_brief_and_says_what_is_wrong_with_a_bad_one(
    project: Paths,
    tmp_path: Path,
) -> None:
    with pytest.raises(DesignError, match="falta un brief"):
        design_cli.make_proposal(project, source=None, base=None, name=None)
    with pytest.raises(DesignError, match="no se puede leer"):
        design_cli.make_proposal(project, source=tmp_path / "nada.json", base=None, name=None)
    broken = tmp_path / "roto.json"
    broken.write_text('{"source": "magia"}', encoding="utf-8")
    with pytest.raises(DesignError, match="no es un brief válido"):
        design_cli.make_proposal(project, source=broken, base=None, name=None)


def test_apply_replaces_the_contract_records_the_decisions_and_builds(
    project: Paths,
    tmp_path: Path,
) -> None:
    project.design_md.write_text(
        f"# D\n\n{DECISIONS_HEADING}\n\n<!-- nota -->\n\n{PROVENANCE_HEADING}\n\n<!-- origen -->\n",
        encoding="utf-8",
    )
    source = write_brief(tmp_path / "brief.json")
    slug, proposal = design_cli.make_proposal(
        project, source=source, base=None, name="spa", today=TODAY
    )

    report = design_cli.apply_proposal(project, slug, force=False, today=TODAY)

    assert load_contract(project.contract) == proposal.contract
    assert report.contract == proposal.contract
    assert "kiro:brand:start" in project.css.read_text(encoding="utf-8")
    text = project.design_md.read_text(encoding="utf-8")
    assert "`brand.primary` [D1]" in text
    assert "https://ejemplo.test/web" in text
    # Applying again is a no-op for DESIGN.md.
    design_cli.apply_proposal(project, slug, force=False, today=TODAY)
    assert project.design_md.read_text(encoding="utf-8") == text
    assert (project.work / "backup").is_dir()


def test_apply_will_not_overwrite_an_identity_of_the_project_without_force(
    project: Paths,
    tmp_path: Path,
) -> None:
    set_contract(project, PRESETS["editorial"].contract)
    slug, proposal = design_cli.make_proposal(
        project, source=write_brief(tmp_path / "b.json"), base=None, name="spa", today=TODAY
    )

    with pytest.raises(DesignError, match="identidad propia"):
        design_cli.apply_proposal(project, slug, force=False, today=TODAY)
    assert load_contract(project.contract) == PRESETS["editorial"].contract

    design_cli.apply_proposal(project, slug, force=True, today=TODAY)
    assert load_contract(project.contract) == proposal.contract
    backups = list((project.work / "backup").glob("*/design.toml"))
    assert (
        backups and parse_contract(backups[0].read_text("utf-8")) == PRESETS["editorial"].contract
    )


def test_apply_lists_the_proposals_there_are_when_the_name_is_wrong(
    project: Paths,
    tmp_path: Path,
) -> None:
    design_cli.make_proposal(
        project, source=write_brief(tmp_path / "b.json"), base=None, name="spa", today=TODAY
    )

    with pytest.raises(DesignError, match=r"no existe la propuesta 'otra'.*spa"):
        design_cli.apply_proposal(project, "otra", force=False)


def test_apply_refuses_a_proposal_edited_into_something_invalid(
    project: Paths,
    tmp_path: Path,
) -> None:
    slug, _ = design_cli.make_proposal(
        project, source=write_brief(tmp_path / "b.json"), base=None, name="spa", today=TODAY
    )
    path = project.proposals / f"{slug}.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["contract"]["brand"]["primary"] = "rojo"
    path.write_text(json.dumps(data), encoding="utf-8")

    with pytest.raises(DesignError, match=r"design\.toml tiene"):
        design_cli.apply_proposal(project, slug, force=True)
    assert load_contract(project.contract).is_default


def test_the_fonts_table_vouches_for_a_source_font(
    project: Paths,
    tmp_path: Path,
) -> None:
    source = write_brief(
        tmp_path / "b.json",
        fonts=[{"name": "SF Pro Display", "role": "body", "category": "sans"}],
    )
    table = tmp_path / "fuentes.json"
    table.write_text('{"SF Pro Display": "Inter"}', encoding="utf-8")

    _, proposal = design_cli.make_proposal(
        project, source=source, base=None, name="x", fonts=table, today=TODAY
    )

    assert proposal.contract.typography.body is not None
    assert proposal.contract.typography.body.name == "Inter"
