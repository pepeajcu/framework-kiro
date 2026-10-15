"""The iOS kit: `surface = "auto"`, the system font, materials and the components.

Pure compiler tests first (text in, text out), then the Jinja components rendered
as a page would, then one real run of Tailwind over the compiled result: the CSS
this kit writes has to be CSS that Tailwind accepts and that does what it says.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from app.branding import contrast_ratio
from app.design_engine import kits
from app.design_engine.blocks import find_block
from app.design_engine.compiler import compile_contract
from app.design_engine.contract import (
    FALLBACKS,
    KITS,
    SURFACES,
    Brand,
    DesignContract,
    DesignError,
    FontFace,
    dump_contract,
    parse_contract,
)
from app.design_engine.fonts import font_family, render_fonts_block_body
from app.design_engine.palette import AA, derive_palette, token_rgb
from app.design_engine.presets import PRESETS
from app.design_engine.runtime import runtime_from_contract
from app.templating import templates
from tests.test_design_engine import ANCHOR_CSS

REPO = Path(__file__).resolve().parent.parent
IOS = PRESETS["ios"].contract


def compiled(contract: DesignContract = IOS) -> str:
    return compile_contract(contract, ANCHOR_CSS).css


# --- The contract ------------


def test_the_new_options_are_documented_in_the_toml() -> None:
    text = dump_contract(IOS)

    assert "auto" in SURFACES and "system" in FALLBACKS and "ios" in KITS
    assert 'kit    = "ios"' in text
    assert 'surface   = "auto"   # light | cream | dark | auto' in text
    assert 'fallback = "system"' in text


def test_kit_is_only_written_when_one_is_used() -> None:
    assert "kit" not in dump_contract(DesignContract())
    assert parse_contract(dump_contract(IOS)) == IOS


@pytest.mark.parametrize("bad", ['kit = "android"', 'kit = "IOS"'])
def test_an_unknown_kit_is_an_error_that_lists_the_options(bad: str) -> None:
    with pytest.raises(DesignError, match=r"structure\.kit.*none \| ios"):
        parse_contract(f"[structure]\n{bad}\n")


def test_the_ios_preset_is_the_documented_one() -> None:
    brand = IOS.brand

    assert (brand.primary, brand.surface, brand.radius) == ("#0066CC", "auto", "0.75rem")
    assert IOS.structure.header == "ios-bar" and IOS.structure.kit == "ios"
    assert IOS.typography.body is not None and IOS.typography.body.fallback == "system"
    assert not derive_palette(brand).failures


def test_apples_system_blue_is_refused_for_a_button_and_the_preset_avoids_it() -> None:
    """Why the preset is #0066CC: the system blue does not carry a white label."""
    from app.design_engine.palette import suggest_primary

    with_white = contrast_ratio((1.0, 1.0, 1.0), (0.0, 0x7A / 255, 1.0))
    assert with_white < AA
    assert suggest_primary("#007AFF") is not None
    assert contrast_ratio((1.0, 1.0, 1.0), (0.0, 0x66 / 255 * 1.0, 0xCC / 255)) >= AA


# --- surface = "auto" ------------


def test_auto_is_light_by_default_and_dark_when_the_system_asks() -> None:
    block = find_block(compiled(), "brand") or ""

    assert "color-scheme: light dark" in block
    media = block.split("@media (prefers-color-scheme: dark)")[1]
    dark = (find_block(compiled(), "brand") or "").split("\n.dark {")[1].split("}")[0]
    # The same dark tokens, once under `.dark` (a band) and once under the media query.
    for token in ("--background", "--foreground", "--primary"):
        value = re.search(rf"{token}: ([^;]+);", dark)
        assert value and value.group(1) in media


def test_auto_redefines_the_dark_variant_so_components_follow_the_system() -> None:
    block = find_block(compiled(), "brand") or ""

    assert "@custom-variant dark {" in block
    assert "&:where(.dark, .dark *)" in block
    assert block.count("@slot;") == 2


@pytest.mark.parametrize("surface", ["light", "cream", "dark"])
def test_a_fixed_surface_has_no_media_query_and_keeps_the_class_variant(surface: str) -> None:
    contract = DesignContract(brand=Brand(surface=surface, neutral="warm"))  # type: ignore[arg-type]
    block = find_block(compiled(contract), "brand") or ""

    assert "prefers-color-scheme" not in block
    assert "@custom-variant" not in block


def test_auto_uses_the_light_palette_not_the_cream_one() -> None:
    auto = derive_palette(Brand(surface="auto", neutral="warm"))
    light = derive_palette(Brand(surface="light", neutral="warm"))

    assert auto.light == light.light and auto.dark == light.dark
    assert auto.auto and not auto.dark_only


def test_auto_passes_aa_in_both_modes() -> None:
    palette = derive_palette(IOS.brand)

    assert not palette.failures
    assert {p.mode for p in palette.pairs} == {"light", "dark"}


def test_auto_tells_the_browser_from_the_first_byte() -> None:
    assert runtime_from_contract(IOS, REPO / "app/static").auto
    assert not runtime_from_contract(DesignContract(), REPO / "app/static").auto
    base = (REPO / "app/templates/base.html").read_text(encoding="utf-8")
    assert '<meta name="color-scheme" content="light dark">' in base


# --- The system font ------------


def test_the_system_font_goes_first_and_the_local_one_second() -> None:
    face = FontFace(name="Inter", weights=(400, 600), fallback="system")

    value = font_family("body", face)

    assert value == '-apple-system, BlinkMacSystemFont, "Inter", sans-serif'
    assert "system-ui" not in value


def test_other_fonts_keep_their_name_first() -> None:
    face = FontFace(name="Fraunces", fallback="serif")

    assert font_family("display", face).startswith('"Fraunces", ui-serif')


def test_the_block_writes_the_whole_family_value_and_the_file_it_needs() -> None:
    body = render_fonts_block_body(IOS.typography) or ""

    assert '--font-sans: -apple-system, BlinkMacSystemFont, "Inter", sans-serif;' in body
    assert "inter-latin-400-normal.woff2" in body and "inter-latin-600-normal.woff2" in body


def test_the_system_font_is_not_preloaded_but_a_local_one_is(tmp_path: Path) -> None:
    fonts = tmp_path / "fonts"
    fonts.mkdir()
    (fonts / "inter-latin-400-normal.woff2").write_bytes(b"x")
    local = DesignContract.model_validate({"type": {"body": {"name": "Inter", "weights": [400]}}})

    assert runtime_from_contract(IOS, tmp_path).preload_fonts == ()
    assert runtime_from_contract(local, tmp_path).preload_fonts == (
        "/static/fonts/inter-latin-400-normal.woff2",
    )


# --- The kit ------------


def test_the_kit_is_compiled_between_its_own_markers_and_only_when_asked() -> None:
    assert find_block(compiled(), "kit") is not None
    assert find_block(compiled(DesignContract()), "kit") is None
    # Turning it off again removes it: nothing stale is left in input.css.
    css = compiled()
    off = IOS.model_copy(update={"structure": IOS.structure.model_copy(update={"kit": "none"})})
    assert find_block(compile_contract(off, css).css, "kit") is None


def test_compiling_twice_changes_nothing() -> None:
    once = compiled()

    assert compile_contract(IOS, once).css == once


def test_the_kit_contains_no_hex_colour_only_tokens() -> None:
    css = kits.IOS_CSS

    assert not re.search(r"#[0-9a-fA-F]{3,8}\b", css)
    assert "var(--card)" in css and "var(--muted-foreground)" in css


def test_the_kit_has_apples_type_scale_and_the_touch_minimum() -> None:
    css = kits.IOS_CSS

    for size in ("2.125rem", "1.75rem", "1.375rem", "1.25rem", "1.0625rem", "0.8125rem"):
        assert size in css
    assert "min-height: 2.75rem" in css  # a row is 44 px
    assert "min-height: 3.0625rem" in css  # a tab is 49 px (Apple's tab bar)
    assert "padding-inline: 1rem" in css and "padding-inline: 1.25rem" in css


def test_a_material_is_solid_unless_blur_is_supported_and_the_person_allows_it() -> None:
    css = kits.IOS_CSS

    solid = css.index(
        ".material-regular,\n.material-thick {\n  background-color: var(--background);"
    )
    supports = css.index("@supports (backdrop-filter: blur(1px))")
    reduced = css.index("@media (prefers-reduced-transparency: reduce), (prefers-contrast: more)")
    assert solid < supports < reduced
    assert "backdrop-filter: none" in css[reduced:]
    # The blur is never written outside the @supports and the "solid again" branches.
    blurs = [m.start() for m in re.finditer(r"backdrop-filter: blur\((?:20|30)px", css)]
    assert len(blurs) == 4  # two materials, each with and without the -webkit- prefix
    assert all(supports < position < reduced for position in blurs)


@pytest.mark.parametrize("name", sorted(PRESETS))
def test_the_material_opacity_keeps_text_at_aa_over_white_and_over_black(name: str) -> None:
    """The point of computing it: Safari does not honour prefers-reduced-transparency."""
    palette = derive_palette(PRESETS[name].contract.brand)

    for tokens in (palette.light, palette.dark):
        alpha = kits.material_alpha(tokens["--background"], tokens["--foreground"])
        assert 0.5 <= alpha <= 1.0
        fg = token_rgb(tokens["--foreground"])
        bg = token_rgb(tokens["--background"])
        for backdrop in (0.0, 1.0):
            mixed = tuple(alpha * c + (1 - alpha) * backdrop for c in bg)
            assert contrast_ratio(fg, mixed) >= AA - 0.01, (name, backdrop)


def test_the_opacities_are_emitted_for_light_dark_and_auto() -> None:
    block = find_block(compiled(), "kit") or ""

    assert re.search(r":root \{\n  --kit-material-alpha: \d+%;", block)
    assert re.search(r"\.dark \{\n  --kit-material-alpha: \d+%;", block)
    assert re.search(
        r"@media \(prefers-color-scheme: dark\) \{\n  :root \{\n    --kit-material-alpha", block
    )
    dark_only = DesignContract(brand=Brand(surface="dark"), structure=IOS.structure)
    assert "\n.dark {" not in (find_block(compiled(dark_only), "kit") or "")


def test_the_thick_material_is_more_opaque_than_the_regular_one() -> None:
    block = find_block(compiled(), "kit") or ""
    regular = int(re.search(r"--kit-material-alpha: (\d+)%", block).group(1))  # type: ignore[union-attr]
    thick = int(re.search(r"--kit-material-alpha-thick: (\d+)%", block).group(1))  # type: ignore[union-attr]

    assert thick > regular and thick <= 100


# --- The components ------------

HOSTILE = '"><script>alert(1)</script>'
IMPORT = (
    '{% from "components/ios.html.jinja" import large_title, grouped_list, list_row, '
    "segmented, tab_bar, sheet, sheet_trigger %}"
)


def render(source: str, **context: object) -> str:
    return templates.env.from_string(IMPORT + source).render(**context)


def test_a_grouped_list_is_a_list_with_a_header_a_footer_and_rows() -> None:
    html = render(
        '{% call grouped_list(header="General", footer="Pie") %}'
        '{{ list_row("Perfil", detail="Ana", href="/perfil", chevron=True) }}'
        '{{ list_row("Salir", destructive=True) }}{% endcall %}'
    )

    assert '<ul class="ios-list" role="list">' in html
    assert 'class="ios-group-header">General<' in html and 'class="ios-group-footer">Pie<' in html
    assert '<a class="ios-row" href="/perfil">' in html
    assert 'aria-hidden="true"' in html  # the chevron is decoration
    assert '<div class="ios-row" data-destructive>' in html
    assert html.count("<li>") == 2


def test_a_row_can_hold_a_control_on_the_right() -> None:
    html = render(
        '{% call list_row("Wi-Fi") %}'
        '<input type="checkbox" role="switch" aria-label="Wi-Fi">{% endcall %}'
    )

    assert html.index("Wi-Fi") < html.index('role="switch"')


def test_everything_a_visitor_can_influence_is_escaped() -> None:
    html = render(
        "{{ large_title(t, subtitle=t) }}"
        "{% call grouped_list(header=t, footer=t) %}"
        "{{ list_row(t, detail=t, href=u) }}{% endcall %}"
        "{{ segmented(t, t, [{'value': t, 'label': t}], selected=t) }}"
        "{{ tab_bar([{'href': u, 'label': t}], u) }}"
        "{% call sheet(t, t) %}{{ t }}{% endcall %}"
        "{{ sheet_trigger(t, t) }}",
        t=HOSTILE,
        u=HOSTILE,
    )

    assert "<script>" not in html
    assert html.count("&lt;script&gt;") >= 10


def test_the_icon_is_the_one_thing_marked_as_markup() -> None:
    html = render(
        '{{ list_row("A", icon=svg) }}'
        '{{ tab_bar([{"href": "/", "label": "B", "icon": svg}], "/") }}',
        svg='<svg aria-hidden="true"></svg>',
    )

    assert html.count('<svg aria-hidden="true"></svg>') == 2


def test_segmented_is_a_named_radio_group_with_the_selected_one_checked() -> None:
    html = render(
        "{{ segmented('vista', 'Vista', [{'value': 'a', 'label': 'Lista'},"
        " {'value': 'b', 'label': 'Mapa'}], selected='b', attrs={'hx-get': '/x'}) }}"
    )

    assert '<fieldset class="ios-segmented">' in html
    assert '<legend class="sr-only">Vista</legend>' in html
    assert html.count('type="radio" name="vista"') == 2
    assert re.search(r'value="b"\s+checked', html) and not re.search(r'value="a"\s+checked', html)
    assert html.count('hx-get="/x"') == 2


def test_the_tab_bar_marks_the_current_page_and_every_tab_has_a_name() -> None:
    html = render(
        "{{ tab_bar([{'href': '/', 'label': 'Inicio'}, {'href': '/notes', 'label': 'Notas'}],"
        " '/notes') }}"
    )

    assert 'aria-label="Secciones"' in html
    assert html.count('aria-current="page"') == 1
    assert re.search(r'href="/notes" aria-current="page"', html)


def test_a_sheet_is_a_native_dialog_closed_by_a_form_without_javascript() -> None:
    html = render('{% call sheet("filtros", "Filtros") %}<p>Contenido</p>{% endcall %}')

    assert '<dialog id="filtros" class="ios-sheet" aria-labelledby="filtros-title">' in html
    assert '<h2 id="filtros-title"' in html
    assert '<form method="dialog">' in html and "<script" not in html
    assert "Contenido" in html


def test_the_components_pass_the_floors_own_audit() -> None:
    from tests.test_ux_floor import audit

    body = render(
        '<main id="main">{{ large_title("Ajustes") }}'
        '{% call grouped_list(header="G") %}'
        '{{ list_row("Perfil", href="/p", chevron=True) }}{% endcall %}'
        "{{ segmented('v', 'Vista', [{'value': 'a', 'label': 'A'}], selected='a') }}"
        "{{ tab_bar([{'href': '/', 'label': 'Inicio'}], '/') }}"
        '{% call sheet("s", "Hoja") %}x{% endcall %}</main>'
    )
    page = (
        '<!doctype html><html lang="es"><head><title>T</title>'
        '<meta name="viewport" content="width=device-width, initial-scale=1"></head><body>'
        f"{body}</body></html>"
    )

    assert audit(page) == []


# --- The header ------------


def test_the_ios_header_keeps_the_brand_and_the_session_logic() -> None:
    header = (REPO / "app/templates/partials/headers/ios-bar.html").read_text(encoding="utf-8")

    assert 'include "partials/brand_mark.html"' in header
    assert 'include "partials/nav_auth.html"' in header
    assert "material-regular" in header and "sticky" in header
    assert "h-12" in header  # 48 px: above the 44 px touch minimum


# --- What Tailwind does with it ------------


def test_tailwind_accepts_the_compiled_kit_and_emits_the_system_dark_variant(
    tmp_path: Path,
) -> None:
    """The compiled CSS is real CSS, and a `dark:` utility follows the system under `auto`."""
    css_dir = tmp_path / "app/static/css"
    css_dir.mkdir(parents=True)
    (tmp_path / "app/templates").mkdir(parents=True)
    (tmp_path / "app/templates/page.html").write_text(
        '<div class="dark:bg-red-500 bg-blue-500 ios-list">x</div>', encoding="utf-8"
    )
    shutil.copy(REPO / "app/static/css/motion.css", css_dir / "motion.css")
    theme = css_dir / "vendor/basecoat"
    theme.mkdir(parents=True)
    (theme / "basecoat-vega.css").write_text("/* vega */")
    (theme / "basecoat-maia.css").write_text("/* maia */")

    source = (REPO / "app/static/css/input.css").read_text(encoding="utf-8")
    (css_dir / "input.css").write_text(compile_contract(IOS, source).css, encoding="utf-8")

    result = subprocess.run(  # noqa: S603
        [
            sys.executable,
            "-m",
            "pytailwindcss",
            "-i",
            str(css_dir / "input.css"),
            "-o",
            str(css_dir / "out.css"),
        ],
        capture_output=True,
        text=True,
        check=False,
        cwd=tmp_path,
    )
    assert result.returncode == 0, result.stderr[-800:]

    out = (css_dir / "out.css").read_text(encoding="utf-8")
    assert re.search(r"\.dark\\:bg-red-500:where\(\.dark, \.dark \*\)", out)
    assert re.search(r"@media \(prefers-color-scheme: dark\) \{\s*\.dark\\:bg-red-500", out)
    assert ".ios-list" in out and "--kit-material-alpha" in out
