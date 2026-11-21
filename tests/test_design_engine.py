"""The design engine: contract, palette, blocks, fonts, presets and motion levels.

Everything here is pure (text in, text out), so nothing touches the network or
the project's real files. The I/O around it is in `test_design_scripts.py`.
"""

from __future__ import annotations

import itertools
import re
import struct
from pathlib import Path

import pytest

from app.branding import (
    BrandError,
    brand_tokens,
    contrast_ratio,
    foreground_for,
    format_oklch,
    oklch_to_rgb,
    parse_hex,
)
from app.design_engine import motion
from app.design_engine.blocks import (
    apply_block,
    apply_theme_block,
    find_block,
    remove_block,
    render_block,
)
from app.design_engine.compiler import compile_contract
from app.design_engine.contract import (
    HEADERS,
    NEUTRALS,
    SURFACES,
    THEMES,
    Brand,
    DesignContract,
    DesignError,
    FontFace,
    dump_contract,
    parse_contract,
)
from app.design_engine.fonts import (
    MAX_FONT_BYTES,
    fallback_stack,
    font_filename,
    render_fonts_block_body,
    required_files,
    validate_woff2,
)
from app.design_engine.palette import (
    AA,
    Palette,
    derive_palette,
    format_ratio,
    neutral_axis,
    render_palette_block,
    suggest_primary,
)
from app.design_engine.presets import PRESETS, get_preset

REPO = Path(__file__).resolve().parent.parent
ANCHOR_CSS = (
    '@import "tailwindcss";\n@import "./vendor/basecoat/basecoat-vega.css";\n\n'
    '@source "../../templates";\n@source "../../../app/**/*.py";\n\n/* mis ajustes */\n'
)


def make_woff2(size: int = 2000, *, tables: int = 5) -> bytes:
    """A minimal buffer with a valid woff2 header (signature, length, table count)."""
    header = b"wOF2" + b"\x00\x01\x00\x00" + struct.pack(">IH", size, tables)
    return header + b"\x00" * (size - len(header))


def parse(toml: str) -> DesignContract:
    return parse_contract(toml)


# --- Contract ---------------------------------------------------------------


def test_the_default_contract_is_basecoats() -> None:
    contract = DesignContract()

    assert contract.is_default
    assert contract.brand.primary == "#171717"
    assert contract.basecoat.theme == "vega"
    assert contract.structure.header == "sticky-blur"


def test_a_full_contract_parses() -> None:
    contract = parse(
        """
        [brand]
        primary = "#c2410c"
        neutral = "warm"
        surface = "cream"
        secondary = ""
        radius = "0.5rem"

        [type]
        display = { name = "Fraunces", weights = ["400", "700"], fallback = "serif" }
        body = { name = "Inter", weights = [400, 600] }

        [basecoat]
        theme = "rhea"

        [motion]
        level = 6

        [structure]
        header = "floating-pill"
        """
    )

    assert contract.brand.primary == "#C2410C"
    assert contract.brand.secondary is None
    assert contract.typography.display is not None
    assert contract.typography.display.weights == (400, 700)
    assert contract.typography.display.fallback == "serif"
    assert contract.motion.level == 6
    assert not contract.is_default


def test_short_hex_is_expanded_and_uppercased() -> None:
    assert parse('[brand]\nprimary = "#0f6"').brand.primary == "#00FF66"


def test_a_bare_zero_radius_becomes_a_length() -> None:
    """`calc(var(--radius) - 4px)` is invalid CSS with a unitless zero inside."""
    assert parse('[brand]\nradius = "0"').brand.radius == "0rem"


@pytest.mark.parametrize(
    ("toml", "fragment"),
    [
        ('[brand]\nprimay = "#fff"', "brand.primay"),  # typo in a key
        ('[brand]\nprimary = "verde"', "hex"),
        ('[brand]\nprimary = ""', "vacío"),
        ('[brand]\nneutral = "hot"', "pure | warm | cool | tinted"),
        ('[brand]\nsurface = "neon"', "light | cream | dark"),
        ('[brand]\nradius = "big"', "radio"),
        ("[motion]\nlevel = 11", "como mucho 10"),
        ("[motion]\nlevel = 0", "al menos 1"),
        ('[basecoat]\ntheme = "bootstrap"', "vega | nova"),
        ('[structure]\nheader = "mega"', "sticky-blur"),
        ('[type]\nbody = { name = "Inter", weights = [450] }', "peso"),
        ('[type]\nbody = { name = "Inter", weights = [] }', "lista de pesos"),
        ("[type]\nbody = { weights = [400] }", "falta"),
        ("[brand", "TOML"),
    ],
)
def test_invalid_contracts_fail_with_a_message_that_says_where(toml: str, fragment: str) -> None:
    with pytest.raises(DesignError) as caught:
        parse(toml)

    assert fragment in str(caught.value)


@pytest.mark.parametrize(
    "name", ["../../etc/passwd", "Inter/../x", "In ter!", "a" * 70, "", "9Inter"]
)
def test_font_names_cannot_smuggle_paths_or_urls(name: str) -> None:
    """The family name ends up in a URL and a file name: it must be boring."""
    with pytest.raises(DesignError):
        parse(f"[type]\nbody = {{ name = {name!r}, weights = [400] }}".replace("'", '"'))


def test_whitespace_in_a_font_name_is_normalised_not_trusted() -> None:
    face = FontFace(name="Inter\n  400\t")

    assert face.name == "Inter 400"
    assert face.slug == "inter-400"


def test_font_slug_matches_fontsource_ids() -> None:
    assert FontFace(name="Plus Jakarta Sans").slug == "plus-jakarta-sans"
    assert FontFace(name="  Inter  ").slug == "inter"


def test_errors_are_collected_not_reported_one_by_one() -> None:
    with pytest.raises(DesignError) as caught:
        parse('[brand]\nprimary = "x"\nneutral = "hot"\n[motion]\nlevel = 99')

    assert "3 errores" in str(caught.value)


@pytest.mark.parametrize("name", sorted(PRESETS))
def test_every_preset_round_trips_through_toml(name: str) -> None:
    contract = PRESETS[name].contract

    assert parse(dump_contract(contract)) == contract


def test_the_projects_design_toml_is_a_valid_contract() -> None:
    """Whatever identity the project chose, the file must parse and compile.

    The framework ships it in the defaults, a configured project in its own
    values: both are fine, a broken one is not.
    """
    contract = parse((REPO / "design.toml").read_text(encoding="utf-8"))

    assert compile_contract(contract, ANCHOR_CSS).palette.failures == ()


# --- Palette ----------------------------------------------------------------


def test_pure_light_reproduces_basecoats_neutrals() -> None:
    """Choosing only a brand colour must not repaint the greys."""
    palette = derive_palette(Brand(primary="#0F766E"))

    assert palette.light["--background"] == "oklch(1.000 0.000 0.0)"
    assert palette.light["--card"] == "oklch(1.000 0.000 0.0)"
    assert palette.light["--muted"] == "oklch(0.970 0.000 0.0)"
    assert palette.light["--border"] == "oklch(0.922 0.000 0.0)"
    assert palette.light["--foreground"] == "oklch(0.145 0.000 0.0)"
    assert palette.dark["--background"] == "oklch(0.145 0.000 0.0)"
    assert palette.dark["--card"] == "oklch(0.205 0.000 0.0)"


def test_the_palette_covers_every_basecoat_colour_token() -> None:
    palette = derive_palette(Brand())
    basecoat = (REPO / "app/static/css/vendor/basecoat/base/base.css").read_text(encoding="utf-8")
    declared = set(re.findall(r"^\s{2}(--[a-z0-9-]+):\s*oklch|^\s{2}(--chart-\d):", basecoat, re.M))
    names = {name for pair in declared for name in pair if name}
    # Basecoat's raw colour variables, minus the ones that are not colours we own.
    assert names, "no se pudieron leer los tokens de Basecoat"

    assert names <= set(palette.light), sorted(names - set(palette.light))
    assert names <= set(palette.dark), sorted(names - set(palette.dark))


COLOURS = ["#171717", "#0F766E", "#C2410C", "#FACC15", "#1E1B4B", "#7C3AED", "#2563EB", "#84CC16"]


@pytest.mark.parametrize(
    ("primary", "neutral", "surface"),
    list(itertools.product(COLOURS, NEUTRALS, SURFACES)),
)
def test_every_combination_reads(primary: str, neutral: str, surface: str) -> None:
    """The point of deriving instead of eyeballing: text always clears AA."""
    palette = derive_palette(Brand(primary=primary, neutral=neutral, surface=surface))  # type: ignore[arg-type]

    assert palette.failures == (), [(p.describe(), round(p.ratio, 2)) for p in palette.failures]


def test_a_colour_that_cannot_carry_button_text_is_reported_with_a_fix() -> None:
    """#E11D48 with Basecoat's light foreground lands at 4.49:1: close, and not AA."""
    contract = DesignContract(brand=Brand(primary="#E11D48"))

    with pytest.raises(DesignError) as caught:
        compile_contract(contract, ANCHOR_CSS)

    message = str(caught.value)
    assert "--primary-foreground sobre --primary" in message
    suggestion = re.search(r"Prueba (#[0-9A-F]{6})", message)
    assert suggestion, message
    fixed = compile_contract(DesignContract(brand=Brand(primary=suggestion.group(1))), ANCHOR_CSS)
    assert fixed.palette.failures == ()


def test_ratios_are_truncated_so_a_failure_never_reads_as_a_pass() -> None:
    assert format_ratio(4.4999) == "4.49"
    assert format_ratio(4.5) == "4.50"
    assert format_ratio(19.79, 1) == "19.7"


def test_the_failure_message_does_not_print_the_minimum_as_the_value() -> None:
    with pytest.raises(DesignError) as caught:
        compile_contract(DesignContract(brand=Brand(primary="#E11D48")), ANCHOR_CSS)

    assert "4.49:1" in str(caught.value)
    assert "4.50:1" not in str(caught.value)


def test_suggest_primary_stays_close_to_the_original() -> None:
    suggestion = suggest_primary("#E11D48")

    assert suggestion is not None
    delta = abs(contrast_ratio(parse_hex(suggestion), parse_hex("#E11D48")))
    assert delta < 1.2  # a nudge, not a different colour


def test_cream_implies_a_warm_axis() -> None:
    hue, chroma = neutral_axis(Brand(surface="cream", neutral="pure"))

    assert chroma > 0
    assert 60 < hue < 100


def test_tinted_neutrals_follow_the_brand_hue() -> None:
    teal = neutral_axis(Brand(primary="#0F766E", neutral="tinted"))[0]
    orange = neutral_axis(Brand(primary="#C2410C", neutral="tinted"))[0]

    assert abs(teal - orange) > 60


def test_one_temperature_per_palette() -> None:
    """Every grey shares one hue: a warm background cannot get a cool border."""
    palette = derive_palette(Brand(neutral="warm", surface="cream"))
    hues = {
        float(palette.light[name].removeprefix("oklch(").split()[2].rstrip(")"))
        for name in ("--background", "--muted", "--border", "--foreground")
    }

    assert len(hues) == 1


def test_cream_with_cool_greys_is_flagged() -> None:
    palette = derive_palette(Brand(neutral="cool", surface="cream"))

    assert any("temperaturas" in warning for warning in palette.warnings)


def test_a_dark_surface_puts_the_dark_palette_on_root() -> None:
    palette = derive_palette(Brand(primary="#84CC16", surface="dark"))

    assert palette.dark_only
    assert palette.light == palette.dark
    assert float(palette.light["--background"].split()[0].removeprefix("oklch(")) < 0.2
    block = render_palette_block(palette, radius="0.5rem")
    assert "color-scheme: dark;" in block.split(".dark")[0]


def test_a_dark_surface_keeps_the_brand_colour_instead_of_repainting_it() -> None:
    """A dark-only project chose its colour on dark: lift it only if it vanishes."""
    visible = derive_palette(Brand(primary="#F97316", surface="dark"))
    assert visible.light["--primary"].startswith("oklch(0.70")  # orange-500, untouched

    sinking = derive_palette(Brand(primary="#1E1B4B", surface="dark"))
    lightness = float(sinking.light["--primary"].split()[0].removeprefix("oklch("))
    assert lightness > 0.3  # lifted until it reaches 3:1 on the background


def test_a_secondary_colour_becomes_the_secondary_token_and_tints_the_accent() -> None:
    plain = derive_palette(Brand(primary="#C2410C"))
    navy = derive_palette(Brand(primary="#C2410C", secondary="#1E3A5F"))

    assert plain.light["--secondary"] == plain.light["--muted"]
    assert navy.light["--secondary"] != navy.light["--muted"]
    assert navy.light["--accent"] != plain.light["--accent"]
    assert navy.failures == ()


def test_charts_follow_the_brand_hue() -> None:
    palette = derive_palette(Brand(primary="#C2410C"))

    hue = float(palette.light["--chart-3"].split()[2].rstrip(")"))
    assert 20 < hue < 60  # orange, not Basecoat's blue


def test_the_audit_measures_what_is_written() -> None:
    """Pairs are computed from the very strings that land in the CSS."""
    palette = derive_palette(Brand(primary="#0F766E", neutral="warm", surface="cream"))
    pair = next(
        p
        for p in palette.pairs
        if p.mode == "light"
        and p.foreground == "--muted-foreground"
        and p.background == "--background"
    )

    def rgb(css: str) -> tuple[float, float, float]:
        value = css.removeprefix("oklch(").removesuffix(")").split("/")[0].split()
        return oklch_to_rgb(float(value[0]), float(value[1]), float(value[2]))

    expected = contrast_ratio(
        rgb(palette.light["--muted-foreground"]), rgb(palette.light["--background"])
    )
    assert pair.ratio == pytest.approx(expected)
    assert pair.ratio >= AA


def test_brand_colour_as_text_is_an_advisory_not_a_failure() -> None:
    """Yellow on white cannot be body text, but it is a legitimate brand colour."""
    palette = derive_palette(Brand(primary="#FACC15"))

    assert palette.failures == ()
    assert any(p.foreground == "--primary" for p in palette.advisories)


def test_the_palette_block_re_maps_theme_colours_under_dark() -> None:
    """Without this, `<section class="dark">` in a light page stays light.

    Basecoat declares `--color-background: var(--background)` on :root, and a
    custom property holding a var() is resolved where it is declared.
    """
    block = render_palette_block(derive_palette(Brand()), radius="0.5rem")
    dark = block.split(".dark {", 1)[1]

    assert "--color-background: var(--background);" in dark
    assert "--color-primary-foreground: var(--primary-foreground);" in dark
    assert "--color-sidebar-ring: var(--sidebar-ring);" in dark
    assert "--color-background" not in block.split(".dark {", 1)[0]


def test_radius_lands_in_the_palette_block() -> None:
    block = render_palette_block(derive_palette(Brand()), radius="0.25rem", source="design.toml")

    assert "--radius: 0.25rem;" in block
    assert "design.toml" in block


# --- brand_tokens (the three-token core the palette builds on) --------------


def test_foreground_is_measured_against_the_colour_it_emits() -> None:
    """`oklch(0.985)` is not pure white; reporting white's contrast would flatter it."""
    css, ratio = foreground_for(parse_hex("#0F766E"))
    real = contrast_ratio(parse_hex("#0F766E"), oklch_to_rgb(0.985, 0.0, 0.0))

    assert css.startswith("oklch(0.985")
    assert ratio == pytest.approx(real)


def test_a_dark_surface_brand_token_is_lifted_only_as_far_as_needed() -> None:
    background = oklch_to_rgb(0.145, 0.0, 0.0)
    default = brand_tokens("#1E1B4B")
    minimal = brand_tokens(
        "#1E1B4B", dark_background=background, min_dark_lightness=0.0, min_dark_contrast=3.0
    )

    default_l = float(default.dark["--primary"].split()[0].removeprefix("oklch("))
    minimal_l = float(minimal.dark["--primary"].split()[0].removeprefix("oklch("))
    assert default_l >= 0.72
    assert 0.3 < minimal_l < default_l


def test_format_oklch_with_alpha() -> None:
    assert format_oklch(0.985, 0.01, 80, 0.1) == "oklch(0.985 0.010 80.0 / 10%)"
    assert format_oklch(0.5, 0.1, 20) == "oklch(0.500 0.100 20.0)"


# --- Blocks and compiler ----------------------------------------------------


def test_apply_block_is_idempotent_and_replaces_in_place() -> None:
    first = apply_block(ANCHOR_CSS, "fonts", render_block("fonts", "a { b: c }"))
    again = apply_block(first, "fonts", render_block("fonts", "a { b: c }"))
    changed = apply_block(first, "fonts", render_block("fonts", "x { y: z }"))

    assert first == again
    assert changed.count("kiro:fonts:start") == 1
    assert "x { y: z }" in changed
    assert "a { b: c }" not in changed


def test_blocks_leave_the_projects_own_css_alone() -> None:
    built = apply_block(ANCHOR_CSS, "fonts", render_block("fonts", "a {}"))

    assert "/* mis ajustes */" in built
    assert built.index("kiro:fonts:end") < built.index("/* mis ajustes */")


def test_a_block_without_its_anchor_fails_loudly() -> None:
    with pytest.raises(DesignError, match="@source"):
        apply_block("body {}", "fonts", render_block("fonts", "a {}"))


def test_remove_block_leaves_clean_text() -> None:
    built = apply_block(ANCHOR_CSS, "fonts", render_block("fonts", "a {}"))

    assert remove_block(built, "fonts") == ANCHOR_CSS
    assert find_block(built, "fonts") is not None
    assert find_block(ANCHOR_CSS, "fonts") is None


def test_the_theme_import_is_wrapped_then_swapped() -> None:
    wrapped = apply_theme_block(ANCHOR_CSS, "lyra")
    swapped = apply_theme_block(wrapped, "sera")

    assert 'basecoat-lyra.css";' in wrapped
    assert "basecoat-vega" not in wrapped
    assert 'basecoat-sera.css";' in swapped
    assert swapped.count("kiro:theme:start") == 1


def test_a_project_without_a_theme_import_gets_an_error() -> None:
    with pytest.raises(DesignError, match="tema de Basecoat"):
        apply_theme_block('@import "tailwindcss";', "nova")


@pytest.mark.parametrize("name", sorted(PRESETS))
def test_compiling_is_idempotent(name: str) -> None:
    contract = PRESETS[name].contract
    once = compile_contract(contract, ANCHOR_CSS).css
    twice = compile_contract(contract, once).css

    assert once == twice


def test_compiling_removes_the_fonts_block_when_none_are_declared() -> None:
    with_fonts = compile_contract(PRESETS["minimalista"].contract, ANCHOR_CSS).css
    without = compile_contract(DesignContract(), with_fonts).css

    assert "kiro:fonts:start" in with_fonts
    assert "kiro:fonts:start" not in without


def test_compiling_upgrades_the_legacy_brand_block() -> None:
    """A project from before the engine has a `kiro:brand` block with 3 tokens."""
    from app.branding import apply_brand_block, brand_tokens, render_brand_block

    legacy = apply_brand_block(ANCHOR_CSS, render_brand_block(brand_tokens("#0F766E")))
    upgraded = compile_contract(DesignContract(brand=Brand(primary="#0F766E")), legacy).css

    assert upgraded.count("kiro:brand:start") == 1
    assert "--background" in upgraded


def test_three_contracts_differ_in_surface_type_and_theme_not_only_in_colour() -> None:
    """The KPI of the plan, at the CSS level: not 'the same grey with another button'."""
    outputs = {
        name: compile_contract(PRESETS[name].contract, ANCHOR_CSS).css
        for name in ("minimalista", "brutalista", "suave-premium")
    }

    def declared(css: str, token: str) -> str:
        brand_block = find_block(css, "brand") or ""
        light = brand_block.split("\n.dark {")[0]
        return re.search(rf"{re.escape(token)}: ([^;]+);", light).group(1)  # type: ignore[union-attr]

    for token in ("--background", "--foreground", "--border", "--radius"):
        values = {declared(css, token) for css in outputs.values()}
        assert len(values) == 3, f"{token} no varía entre estilos: {values}"
    assert len({re.search(r"basecoat-(\w+)\.css", css).group(1) for css in outputs.values()}) == 3  # type: ignore[union-attr]
    fonts = {
        re.search(r"--font-display|--font-sans: \"([^\"]+)\"", css) is not None
        for css in outputs.values()
    }
    assert fonts == {True}


# --- Fonts ------------------------------------------------------------------


def test_a_woff2_header_is_validated() -> None:
    validate_woff2(make_woff2(), label="ok")  # does not raise


@pytest.mark.parametrize(
    ("data", "fragment"),
    [
        (b"<html>" + b"x" * 2000, "no es un woff2"),
        (make_woff2(2000)[:1500], "truncado"),
        (b"wOF2", "pequeño"),
        (make_woff2(MAX_FONT_BYTES + 10), "pesa"),
        (make_woff2(2000, tables=0), "tablas"),
    ],
)
def test_bad_font_files_are_refused(data: bytes, fragment: str) -> None:
    with pytest.raises(DesignError, match=fragment):
        validate_woff2(data, label="x.woff2")


def test_required_files_lists_every_weight_once() -> None:
    contract = parse(
        '[type]\ndisplay = { name = "Inter", weights = [400, 700] }\n'
        'body = { name = "Inter", weights = [400] }'
    )

    names = [file.filename for file in required_files(contract.typography)]

    assert names == ["inter-latin-400-normal.woff2", "inter-latin-700-normal.woff2"]
    assert font_filename("plus-jakarta-sans", 600) == "plus-jakarta-sans-latin-600-normal.woff2"


def test_the_fonts_block_declares_faces_tokens_and_headings() -> None:
    body = render_fonts_block_body(PRESETS["suave-premium"].contract.typography)

    assert body is not None
    assert body.count("@font-face") == 4
    assert 'font-family: "Fraunces";' in body
    assert "font-display: swap;" in body
    assert 'url("/static/fonts/fraunces-latin-400-normal.woff2")' in body
    assert '--font-display: "Fraunces", ui-serif' in body
    assert '--font-sans: "Plus Jakarta Sans", ui-sans-serif' in body
    assert "font-family: var(--font-display);" in body


def test_no_heading_rule_without_a_display_font() -> None:
    body = render_fonts_block_body(PRESETS["panel-de-datos"].contract.typography)

    assert body is not None
    assert "var(--font-display)" not in body
    assert "--font-mono:" in body


def test_a_project_with_no_fonts_has_no_block_body() -> None:
    assert render_fonts_block_body(DesignContract().typography) is None


def test_fallback_stacks_follow_the_declared_kind() -> None:
    serif = FontFace(name="Fraunces", fallback="serif")
    plain = FontFace(name="Inter")

    assert "serif" in fallback_stack("display", serif)
    assert "system-ui" in fallback_stack("body", plain)
    assert "monospace" in fallback_stack("mono", plain)


# --- Presets ----------------------------------------------------------------


@pytest.mark.parametrize("name", sorted(PRESETS))
def test_every_preset_is_a_valid_readable_contract(name: str) -> None:
    preset = PRESETS[name]
    compiled = compile_contract(preset.contract, ANCHOR_CSS)

    assert preset.name == name
    assert compiled.palette.failures == ()
    assert preset.contract.motion.level == preset.motion
    assert not preset.contract.is_default
    assert (REPO / ".claude/skills/kiro-design/references" / preset.reference).is_file(), (
        f"falta la referencia {preset.reference}"
    )
    assert (
        REPO / "app/templates/partials/headers" / f"{preset.contract.structure.header}.html"
    ).is_file()


def test_presets_differ_on_several_axes_not_one() -> None:
    """A preset that only changes a colour is the problem this engine exists to fix."""
    # `estandar-shadcn` is the framework's own look on purpose: it is not an identity.
    contracts = [p.contract for n, p in PRESETS.items() if n != "estandar-shadcn"]

    assert len({c.basecoat.theme for c in contracts}) >= 5
    assert len({c.structure.header for c in contracts}) >= 4
    assert len({c.brand.radius for c in contracts}) >= 4
    assert len({c.typography.body.name for c in contracts if c.typography.body}) >= 5


def test_an_unknown_style_lists_the_options() -> None:
    with pytest.raises(DesignError, match="minimalista"):
        get_preset("barroco")


def test_the_skill_table_matches_the_code() -> None:
    """The skill is what the AI reads, the presets are what runs: they must agree."""
    skill = (REPO / ".claude/skills/kiro-design/SKILL.md").read_text(encoding="utf-8")

    for name, preset in PRESETS.items():
        row = next((line for line in skill.splitlines() if line.startswith(f"| `{name}`")), None)
        assert row is not None, f"la tabla de la skill no tiene una fila para {name}"
        contract = preset.contract
        assert f"{preset.variance} / {preset.motion} / {preset.density}" in row, name
        assert f"`{contract.basecoat.theme}`" in row, name
        assert f"`{contract.structure.header}`" in row, name
        assert preset.reference in row, name


def test_every_documented_option_exists_in_the_contract() -> None:
    """The toml template lists options; they must be the ones the models accept."""
    text = dump_contract(DesignContract())

    for option in (*NEUTRALS, *SURFACES, *THEMES, *HEADERS):
        assert option in text


# --- Motion levels ----------------------------------------------------------


@pytest.mark.parametrize(
    ("level", "engine"),
    [
        (1, "css"),
        (3, "css"),
        (4, "core"),
        (6, "core"),
        (7, "motion"),
        (8, "motion"),
        (9, "gsap"),
        (10, "gsap"),
    ],
)
def test_levels_map_to_engines(level: int, engine: str) -> None:
    assert motion.engine_for(level) == engine


def test_low_levels_load_nothing(tmp_path: Path) -> None:
    assert motion.scripts_for(3, tmp_path) == ((), ())
    assert motion.missing_files(3, tmp_path) == ()


def test_scripts_are_loaded_only_when_they_exist(tmp_path: Path) -> None:
    js = tmp_path / "js"
    (js / "vendor").mkdir(parents=True)
    (js / "motion.js").write_text("//")

    # Level 8 wants Motion and its adapter; neither is there: core only.
    assert motion.scripts_for(8, tmp_path) == (("js/motion.js",), ())
    assert set(motion.missing_files(8, tmp_path)) == {
        "js/motion-lib.js",
        "js/vendor/motion.min.js",
    }

    (js / "motion-lib.js").write_text("//")
    (js / "vendor" / "motion.min.js").write_text("//")
    _, body = motion.scripts_for(8, tmp_path)
    # The library goes before its adapter.
    assert body == ("js/vendor/motion.min.js", "js/motion-lib.js")
    assert motion.missing_files(8, tmp_path) == ()


def test_an_adapter_is_never_loaded_without_its_library(tmp_path: Path) -> None:
    (tmp_path / "js" / "vendor").mkdir(parents=True)
    for name in ("motion.js", "motion-gsap.js", "vendor/gsap.min.js"):  # no ScrollTrigger
        (tmp_path / "js" / name).write_text("//")

    assert motion.scripts_for(9, tmp_path)[1] == ()


def test_gsap_replaces_motion_instead_of_stacking() -> None:
    assert motion.vendored_files(9) == (motion.VENDOR_GSAP, motion.VENDOR_SCROLLTRIGGER)
    assert motion.vendored_files(8) == (motion.VENDOR_MOTION,)
    assert motion.vendored_files(5) == ()


def test_the_vocabulary_is_implemented_by_the_script_that_owns_it() -> None:
    """Every `data-motion` value the checker accepts has code behind it, and vice versa."""
    js = REPO / "app/static/js"

    def registered(name: str) -> set[str]:
        return set(re.findall(r'register\("([a-z-]+)"', (js / name).read_text(encoding="utf-8")))

    core = (js / "motion.js").read_text(encoding="utf-8")
    builtin = set(re.findall(r'^    "?([a-z-]+)"?: function', core, re.M))

    by_level = {
        level: {value for value, needed in motion.VOCABULARY.items() if needed == level}
        for level in (4, 7, 9)
    }
    assert builtin == by_level[4]
    assert registered("motion-lib.js") == by_level[7]
    # GSAP is a superset of Motion: a project at level 9 keeps what it had at 7.
    assert registered("motion-gsap.js") == by_level[7] | by_level[9]


def test_hidden_states_only_exist_under_the_js_motion_gate() -> None:
    """The invariant behind 'content is visible without JavaScript' (AGENTS.md rule 3)."""
    css = (REPO / "app/static/css/motion.css").read_text(encoding="utf-8")
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    # The reduced-motion block *forces* visibility; it is the opposite of hiding.
    css = re.sub(r"@media \(prefers-reduced-motion: reduce\) \{.*?\n\}\n", "", css, flags=re.S)

    hiding = [
        (selectors, body)
        for selectors, body in re.findall(r"([^{}@]+)\{([^{}]*)\}", css)
        if re.search(r"opacity:\s*0\s*;|visibility:\s*hidden|translate3d\(0,\s*1[01]0%", body)
    ]

    assert hiding, "no se encontró ningún estado oculto: ¿cambió el CSS?"
    for selectors, body in hiding:
        for selector in selectors.split(","):
            selector = selector.strip()
            assert selector.startswith(".js-motion") or selector.startswith(".m-split"), (
                f"`{selector}` oculta contenido sin la puerta .js-motion: {body.strip()}"
            )


def test_the_core_script_respects_reduced_motion_and_old_browsers() -> None:
    source = (REPO / "app/static/js/motion.js").read_text(encoding="utf-8")

    assert "prefers-reduced-motion: reduce" in source
    assert '"IntersectionObserver" in window' in source
    # The gate class is added only after both checks, never before.
    assert source.index("prefers-reduced-motion") < source.index('classList.add("js-motion")')


def test_the_core_script_cleans_up_after_htmx() -> None:
    source = (REPO / "app/static/js/motion.js").read_text(encoding="utf-8")

    assert "htmx:load" in source
    assert "htmx:beforeCleanupElement" in source
    assert "onCleanup" in source


def test_a_palette_is_a_frozen_value() -> None:
    palette = derive_palette(Brand())

    assert isinstance(palette, Palette)
    with pytest.raises(AttributeError):
        palette.dark_only = True  # type: ignore[misc]


def test_brand_error_is_the_base_of_design_error() -> None:
    """The scripts catch `BrandError`; design errors must travel the same road."""
    assert issubclass(DesignError, BrandError)
