"""Compiled density and the three states.

`VISUAL_DENSITY` used to be a number in `DESIGN.md` that nothing read. It is now
`[structure] density`, compiled to the vertical rhythm every template follows through the
`section-y`, `gap-rhythm` and `min-h-row` utilities.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from scripts import design as design_cli

from app.design_engine import rhythm
from app.design_engine.blocks import find_block
from app.design_engine.checks import run_checks
from app.design_engine.compiler import compile_contract
from app.design_engine.contract import DesignContract, DesignError, dump_contract, parse_contract
from app.design_engine.paths import Paths
from app.design_engine.presets import PRESETS
from app.templating import templates
from tests.test_design_engine import ANCHOR_CSS

REPO = Path(__file__).resolve().parent.parent


def with_density(value: int) -> DesignContract:
    return DesignContract.model_validate({"structure": {"density": value}})


# --- The contract --------


def test_density_defaults_to_the_middle_and_is_only_written_when_it_is_not() -> None:
    assert DesignContract().structure.density == 5
    assert "density" not in dump_contract(DesignContract())

    text = dump_contract(with_density(8))

    assert "density = 8   # 1 aireado ... 10 denso" in text
    assert parse_contract(text) == with_density(8)


@pytest.mark.parametrize("bad", ["0", "11", '"denso"', "5.5"])
def test_density_is_a_whole_number_from_one_to_ten(bad: str) -> None:
    with pytest.raises(DesignError, match=r"structure\.density"):
        parse_contract(f"[structure]\ndensity = {bad}\n")


@pytest.mark.parametrize("name", sorted(PRESETS))
def test_a_preset_density_is_the_one_its_dial_says(name: str) -> None:
    """The dial in the docs and the value that gets compiled must be the same number."""
    preset = PRESETS[name]

    assert preset.contract.structure.density == preset.density


def test_design_set_changes_the_density(tmp_path: Path) -> None:
    paths = Paths(tmp_path)
    paths.contract.write_text(dump_contract(DesignContract()), encoding="utf-8")

    design_cli.set_values(paths, ["structure.density=8"])

    assert parse_contract(paths.contract.read_text("utf-8")).structure.density == 8


# --- The compiled rhythm --------


def test_the_rhythm_goes_from_airy_to_packed() -> None:
    airy, packed = rhythm.measures(1), rhythm.measures(10)

    assert airy["section-y"] > packed["section-y"] * 3
    assert airy["gap"] > packed["gap"] and airy["row-h"] > packed["row-h"]
    assert all(rhythm.SECTION_Y[i] >= rhythm.SECTION_Y[i + 1] for i in range(9)), (
        "la densidad debe estrechar el ritmo de forma monótona"
    )
    assert list(rhythm.GAP) == sorted(rhythm.GAP, reverse=True)
    assert list(rhythm.ROW_H) == sorted(rhythm.ROW_H, reverse=True)


def test_the_block_declares_the_variables_and_the_three_utilities() -> None:
    block = rhythm.render_rhythm_block(5)

    assert "--kiro-section-y: 5rem;" in block
    for utility in ("section-y", "gap-rhythm", "min-h-row"):
        assert f"@utility {utility} {{" in block
    assert block.startswith("/* kiro:rhythm:start")


def test_a_phone_gets_a_tighter_section_and_a_dense_row_never_goes_below_a_finger() -> None:
    dense = rhythm.render_rhythm_block(10)
    airy = rhythm.render_rhythm_block(1)

    assert "@media (max-width: 767px)" in dense
    assert re.search(r"@media \(pointer: coarse\) \{\s+:root \{ --kiro-row-h: 2\.75rem; \}", dense)
    # An airy row is already taller than 44 px: nothing to raise.
    assert "pointer: coarse" not in airy


def test_every_density_compiles_idempotently_and_always_has_the_block() -> None:
    for density in range(1, 11):
        css = compile_contract(with_density(density), ANCHOR_CSS).css

        assert find_block(css, "rhythm") is not None
        assert compile_contract(with_density(density), css).css == css


def test_changing_the_density_replaces_the_block_it_does_not_add_another() -> None:
    first = compile_contract(with_density(2), ANCHOR_CSS).css
    second = compile_contract(with_density(9), first).css

    assert second.count("kiro:rhythm:start") == 1
    assert "--kiro-section-y: 2.5rem;" in second and "--kiro-section-y: 8rem" not in second


def test_the_committed_input_css_already_has_the_default_rhythm() -> None:
    css = (REPO / "app/static/css/input.css").read_text(encoding="utf-8")

    assert find_block(css, "rhythm") == rhythm.render_rhythm_block(5)


# --- What Tailwind does with it --------


def test_tailwind_emits_the_rhythm_utilities_only_when_a_template_uses_them(tmp_path: Path) -> None:
    css_dir = tmp_path / "app/static/css"
    css_dir.mkdir(parents=True)
    (tmp_path / "app/templates").mkdir(parents=True)
    (tmp_path / "app/templates/page.html").write_text(
        '<section class="section-y"><div class="gap-rhythm min-h-row">x</div></section>',
        encoding="utf-8",
    )
    shutil.copy(REPO / "app/static/css/motion.css", css_dir / "motion.css")
    theme = css_dir / "vendor/basecoat"
    theme.mkdir(parents=True)
    (theme / "basecoat-vega.css").write_text("/* vega */")
    source = (REPO / "app/static/css/input.css").read_text(encoding="utf-8")
    (css_dir / "input.css").write_text(
        compile_contract(with_density(8), source).css, encoding="utf-8"
    )

    result = subprocess.run(  # noqa: S603
        [sys.executable, "-m", "pytailwindcss", "-i", str(css_dir / "input.css"),
         "-o", str(css_dir / "out.css")],
        capture_output=True, text=True, check=False, cwd=tmp_path,
    )  # fmt: skip
    assert result.returncode == 0, result.stderr[-600:]

    out = (css_dir / "out.css").read_text(encoding="utf-8")
    assert re.search(r"\.section-y\s*\{\s*padding-block: var\(--kiro-section-y\)", out)
    assert re.search(r"\.gap-rhythm\s*\{\s*gap: var\(--kiro-gap\)", out)
    assert re.search(r"\.min-h-row\s*\{\s*min-height: var\(--kiro-row-h\)", out)
    assert "--kiro-section-y: 3rem" in out  # density 8


# --- design-check against DESIGN.md ---------


def _project(tmp_path: Path, density: int, dial: str) -> Paths:
    paths = Paths(tmp_path)
    (paths.static / "css").mkdir(parents=True)
    shutil.copy(REPO / "app/static/css/input.css", paths.css)
    theme = paths.basecoat
    theme.mkdir(parents=True)
    (theme / "basecoat-vega.css").write_text("/* vega */")
    shutil.copytree(REPO / "app/templates/partials/headers", paths.headers)
    (paths.static / "js").mkdir()
    paths.contract.write_text(dump_contract(with_density(density)), encoding="utf-8")
    paths.design_md.write_text(
        f"# D\n\n## Firma visual\n\n1. algo\n\n| `VISUAL_DENSITY` | {dial} | galería | cabina |\n",
        encoding="utf-8",
    )
    design_cli.build(paths)
    return paths


def test_design_check_warns_when_the_dial_and_the_contract_disagree(tmp_path: Path) -> None:
    paths = _project(tmp_path, density=8, dial="3")

    findings = [f for f in run_checks(paths, allow_defaults=True) if "VISUAL_DENSITY" in f.message]

    assert len(findings) == 1 and findings[0].level == "warn"
    assert "structure.density = 8" in findings[0].message


def test_design_check_is_quiet_when_they_agree(tmp_path: Path) -> None:
    paths = _project(tmp_path, density=8, dial="8")

    assert not [f for f in run_checks(paths, allow_defaults=True) if "VISUAL_DENSITY" in f.message]


# --- The three states --------

IMPORT = '{% from "components/states.html.jinja" import loading, empty, error_state %}'


def render(source: str, **context: object) -> str:
    return templates.env.from_string(IMPORT + source).render(**context)


def test_loading_is_a_polite_status_with_a_skeleton_of_the_requested_shape() -> None:
    html = render('{{ loading(rows=4, label="Buscando") }}')

    assert 'role="status"' in html and 'aria-busy="true"' in html and 'aria-live="polite"' in html
    assert html.count('class="skeleton') == 4
    assert "Buscando…" in html and "sr-only" in html


def test_empty_says_what_it_is_and_offers_the_way_to_fill_it() -> None:
    html = render(
        '{{ empty("Sin notas", "Escribe la primera.", href="/notes/new", action="Crear") }}'
    )

    assert "Sin notas" in html and "Escribe la primera." in html
    assert 'href="/notes/new"' in html and "Crear" in html
    assert "<a " not in render('{{ empty("Sin notas") }}')


def test_an_error_is_an_alert_and_the_retry_button_is_optional() -> None:
    html = render(
        '{{ error_state("No cargó", "Prueba de nuevo.", '
        'retry={"hx-get": "/x", "hx-target": "#r"}) }}'
    )

    assert 'role="alert"' in html and 'hx-get="/x"' in html and 'hx-target="#r"' in html
    assert "Reintentar" in html
    assert "<button" not in render('{{ error_state("No cargó") }}')


def test_everything_the_states_print_is_escaped() -> None:
    hostile = '"><script>alert(1)</script>'

    html = render(
        "{{ loading(label=t) }}{{ empty(t, t, href=t, action=t) }}"
        "{{ error_state(t, t, retry={'hx-get': t}, label=t) }}",
        t=hostile,
    )

    assert "<script>" not in html and "&lt;script&gt;" in html


def test_the_notes_page_uses_the_empty_state(logged_in_client) -> None:  # type: ignore[no-untyped-def]
    page = logged_in_client.get("/notes").text

    assert "Aún no tienes notas" in page and "border-dashed" in page
