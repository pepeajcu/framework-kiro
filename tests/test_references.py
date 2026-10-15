"""Taking the visual language of a reference: Refero, skillui, Stitch and plain websites.

Each way in is checked against a realistic input (no network: `MockTransport`, a fake
`skillui`), and then every one of them is taken **all the way**: reference, proposal,
apply, and a `design-check` with no errors. The promise is that no source can leave the
project with a contract that does not build.
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

import httpx2
import pytest
from scripts import design as design_cli
from scripts import reference as reference_cli

from app.branding import BrandError
from app.design_engine.checks import run_checks
from app.design_engine.contract import DesignError, load_contract
from app.design_engine.cssread import (
    category_of,
    clean_family,
    find_colours,
    generic_of,
    radius_from,
    role_of,
)
from app.design_engine.external_md import brief_from_markdown
from app.design_engine.paths import Paths
from app.design_engine.skillui import brief_from_skillui
from tests.test_design_scripts import fontsource

FIXTURES = Path(__file__).resolve().parent / "fixtures"
REFERO = (FIXTURES / "refero_style.md").read_text(encoding="utf-8")
STITCH = (FIXTURES / "stitch_dark.md").read_text(encoding="utf-8")


# --- Reading CSS values --------


def test_colours_are_read_in_every_css_notation() -> None:
    text = (
        "a { color: #0F766E } b { color: #fff } c { color: #0f766e80 }"
        " d { color: rgb(0, 102, 204) } e { color: rgba(0 102 204 / 0.5) }"
        " f { color: hsl(210, 100%, 40%) } g { color: rgb(10% 20% 30%) } h { color: var(--x) }"
    )

    assert find_colours(text) == [
        "#0F766E", "#FFFFFF", "#0F766E", "#0066CC", "#0066CC", "#0066CC", "#1A334D",
    ]  # fmt: skip


@pytest.mark.parametrize(
    ("raw", "family"),
    [
        ('"Inter Variable", system-ui, sans-serif', "Inter"),
        ("'Plus Jakarta Sans', sans-serif", "Plus Jakarta Sans"),
        ("system-ui, sans-serif", None),
        ("Arial, Helvetica, sans-serif", None),
        ("-apple-system, BlinkMacSystemFont, 'Segoe UI'", None),
        ("var(--font-sans)", None),
        ("source-sans-pro, sans-serif", "source sans pro"),
        ("<script>", None),
    ],
)
def test_a_font_family_is_the_first_real_choice(raw: str, family: str | None) -> None:
    assert clean_family(raw) == family


def test_categories_come_from_the_generic_family_first_then_from_the_name() -> None:
    assert generic_of("Foo, serif") == "serif" and generic_of("Foo, sans-serif") is None
    assert generic_of("Foo, ui-monospace") == "mono"
    assert category_of("Playfair Display") == "serif"
    assert category_of("JetBrains Mono") == "mono"
    assert category_of("Inter") is None
    assert category_of("Inter", "serif") == "serif"


@pytest.mark.parametrize(
    ("values", "expected"),
    [
        (["8px", "8px", "12px"], "0.5rem"),
        (["12px 12px 0 0", "12px"], "0.75rem"),
        (["999px", "9999px", "50%", "8px"], "0.5rem"),
        (["0", "0px"], "0rem"),
        (["999px", "50%"], None),
        ([], None),
    ],
)
def test_the_radius_is_the_one_used_most_and_a_pill_is_not_a_radius(
    values: list[str], expected: str | None
) -> None:
    assert radius_from(values) == expected


@pytest.mark.parametrize(
    ("label", "role"),
    [
        ("Primary / CTA, links", "primary"),
        ("Secondary accent", "secondary"),
        ("Page background", "background"),
        ("Body text and headings", "text"),
        ("text-primary", "text"),
        ("Muted secondary text", "text"),
        ("Primary button text", "other"),
        ("Card surface", "surface"),
        ("Borders", "other"),
    ],
)
def test_a_colours_role_is_read_from_the_words_around_it(label: str, role: str) -> None:
    assert role_of(label) == role


# --- A pasted Refero or Stitch DESIGN.md --------


def test_a_refero_export_gives_its_accent_fonts_radius_and_rules() -> None:
    brief = brief_from_markdown(REFERO, source="reference", provenance="refero")

    roles = {c.hex: c.role for c in brief.colours}
    assert roles["#0F766E"] == "primary" and roles["#B45309"] == "secondary"
    assert roles["#FAFAF7"] == "background" and roles["#16181D"] == "text"
    fonts = {f.role: f for f in brief.fonts}
    assert fonts["display"].name == "Fraunces" and fonts["display"].category == "serif"
    assert fonts["display"].weights == (600,)
    assert fonts["body"].name == "Inter"  # "Inter Variable", system-ui, sans-serif
    assert fonts["mono"].name == "JetBrains Mono" and fonts["mono"].category == "mono"
    assert brief.radius == "0.75rem"  # the card; the 999px pill is not the radius
    assert brief.title == "Aurora Ledger"
    assert "Add gradients behind text" in brief.anti_patterns
    assert any("one accent colour" in note for note in brief.ux_notes)


def test_a_stitch_document_in_prose_and_lists_is_read_too() -> None:
    brief = brief_from_markdown(STITCH)

    roles = {c.hex: c.role for c in brief.colours}
    assert roles["#38BDF8"] == "primary" and roles["#0A0A0B"] == "background"
    assert roles["#71717A"] == "text"  # "secondary text" is text, not a second brand colour
    fonts = {f.role: f.name for f in brief.fonts}
    assert fonts == {"display": "Space Grotesk", "body": "Inter", "mono": "JetBrains Mono"}
    assert brief.radius == "0.375rem"
    assert (brief.surface, brief.density, brief.motion) == ("dark", 7, 8)
    assert brief.anti_patterns == ("Never use pure white text on the canvas",)


def test_text_that_is_not_a_style_document_is_refused_and_says_what_to_do() -> None:
    with pytest.raises(BrandError, match="design-brief-schema"):
        brief_from_markdown("# Mi producto\n\nUna app para pedir cita en el dentista.\n")


def test_an_enormous_document_is_refused() -> None:
    with pytest.raises(BrandError, match="pesa demasiado"):
        brief_from_markdown("# x\n" + "#0F766E " * 100_000)


def test_markup_in_a_reference_cannot_become_a_font_name_or_a_file_name() -> None:
    hostile = REFERO.replace("Fraunces", "<script>alert(1)</script>").replace(
        "Aurora Ledger", "<img src=x onerror=alert(1)>"
    )

    brief = brief_from_markdown(hostile)

    assert all(re.fullmatch(r"[A-Za-z][A-Za-z0-9 ]*", font.name) for font in brief.fonts)
    assert re.fullmatch(r"[a-z0-9-]+", design_cli._slug(brief.title))


# --- skillui's token files --------

SKILLUI_COLORS = {
    "core": {
        "background": {"value": "#0B0F14", "role": "background"},
        "surface": {"value": "#131A22", "role": "surface"},
        "text-primary": {"value": "#E6EDF3", "role": "text-primary"},
        "accent": {"value": "#2DD4BF", "role": "accent", "name": "Teal"},
    },
    "status": {"danger": {"value": "#F85149"}},
    "extended": {"color-#58a6ff": {"value": "#58A6FF"}},
    "meta": {"theme": "dark", "extracted": "2026-10-14"},
}
SKILLUI_TYPE = {
    "families": ["Space Grotesk", "Inter"],
    "scale": {
        "display": {
            "fontFamily": "'Space Grotesk', sans-serif",
            "fontSize": "56px",
            "fontWeight": "700",
        },
        "h2": {
            "fontFamily": "'Space Grotesk', sans-serif",
            "fontSize": "32px",
            "fontWeight": "700",
        },
        "body": {
            "fontFamily": "Inter, system-ui, sans-serif",
            "fontSize": "16px",
            "fontWeight": "400",
        },
        "code": {
            "fontFamily": "'IBM Plex Mono', monospace",
            "fontSize": "14px",
            "fontWeight": "400",
        },
    },
}
SKILLUI_SPACING = {"base": {"value": "4px"}, "unit": "px", "radius": {"md": "6px", "lg": "6px"}}


def test_skillui_tokens_give_the_palette_the_faces_the_rhythm_and_the_theme() -> None:
    brief = brief_from_skillui(
        colors=SKILLUI_COLORS,
        typography=SKILLUI_TYPE,
        spacing=SKILLUI_SPACING,
        provenance="skillui: https://ejemplo.test",
    )

    roles = {c.hex: c.role for c in brief.colours}
    assert roles["#2DD4BF"] == "primary" and roles["#E6EDF3"] == "text"
    fonts = {f.role: f for f in brief.fonts}
    assert fonts["display"].name == "Space Grotesk" and fonts["display"].weights == (600, 700)
    assert fonts["body"].name == "Inter" and fonts["mono"].category == "mono"
    assert (brief.surface, brief.density, brief.radius) == ("dark", 7, "0.375rem")
    assert brief.provenance == "skillui: https://ejemplo.test"


def test_skillui_fills_what_its_tokens_lack_from_its_design_md() -> None:
    brief = brief_from_skillui(colors=SKILLUI_COLORS, design_md=STITCH, provenance="skillui: x")

    assert brief.motion == 8 and brief.anti_patterns
    assert {f.name for f in brief.fonts} == {"Space Grotesk", "Inter", "JetBrains Mono"}


def test_skillui_with_nothing_readable_says_so() -> None:
    with pytest.raises(BrandError, match=r"tokens/colors\.json"):
        brief_from_skillui(provenance="x")


# --- Reading a website --------

SITE = """<!doctype html><html><head><title>  Casa Verde  Floristas </title>
<link rel="stylesheet" href="/css/site.css"><link rel="icon" href="/x.ico">
<link rel="stylesheet" href="https://cdn.ejemplo.test/lib.css">
<style>.hero { background: #FFFFFF; }</style></head><body><h1>Hola</h1></body></html>"""
SITE_CSS = """
:root { --brand: #166534; --ink: #1C1917 }
html, body { background: #FAF7F2; color: #1C1917; font-family: 'DM Sans', sans-serif }
h1, h2 { font-family: 'Fraunces', Georgia, serif }
code, pre { font-family: 'JetBrains Mono', monospace }
a { color: #166534 }
.btn-primary { background: #166534; color: #FFFFFF; border-radius: 10px; transition: transform .2s }
.btn-primary:hover { background: #14532D }
.card { border-radius: 10px; border: 1px solid #E7E0D6 }
.pill { border-radius: 9999px }
@keyframes rise { from { opacity: 0 } to { opacity: 1 } }
"""


def site_client(requests: list[str] | None = None) -> httpx2.Client:
    def handler(request: httpx2.Request) -> httpx2.Response:
        url = str(request.url)
        if requests is not None:
            requests.append(url)
        if url == "https://casaverde.test/":
            return httpx2.Response(200, content=SITE.encode())
        if url == "https://casaverde.test/css/site.css":
            return httpx2.Response(200, content=SITE_CSS.encode())
        return httpx2.Response(404)

    return httpx2.Client(transport=httpx2.MockTransport(handler))


def test_a_site_gives_its_accent_faces_radius_and_motion_from_its_css() -> None:
    requests: list[str] = []

    brief = reference_cli.capture("https://casaverde.test/", client=site_client(requests))

    roles = {c.hex: c.role for c in brief.colours}
    assert roles["#166534"] == "primary"  # the colour the buttons and links are filled with
    assert roles["#FAF7F2"] == "background"
    fonts = {f.role: f for f in brief.fonts}
    assert fonts["display"].name == "Fraunces" and fonts["display"].category == "serif"
    assert fonts["body"].name == "DM Sans" and fonts["mono"].name == "JetBrains Mono"
    assert brief.radius == "0.625rem"
    assert brief.motion == 4 or brief.motion == 6
    assert brief.title == "Casa Verde Floristas"
    assert brief.provenance.startswith("https://casaverde.test/ (capturado el ")
    # Only the page and its stylesheets, as text: no icon, no image, no font.
    assert "https://casaverde.test/x.ico" not in requests
    assert not any(url.endswith((".woff2", ".png", ".jpg", ".svg", ".ico")) for url in requests)


@pytest.mark.parametrize(
    "url", ["file:///etc/passwd", "ftp://x.test/", "javascript:alert(1)", "casaverde"]
)
def test_only_http_pages_can_be_a_reference(url: str) -> None:
    with pytest.raises(DesignError, match=r"no es una URL http"):
        reference_cli.capture(url)


def test_a_page_without_css_says_why_and_what_to_try() -> None:
    client = httpx2.Client(
        transport=httpx2.MockTransport(lambda r: httpx2.Response(200, content=b"<html><body>hi"))
    )

    with pytest.raises(DesignError, match="skillui"):
        reference_cli.capture("https://vacia.test/", client=client)


def test_a_missing_page_is_an_error_not_a_crash() -> None:
    client = httpx2.Client(transport=httpx2.MockTransport(lambda r: httpx2.Response(404)))

    with pytest.raises(DesignError, match="no existe en el origen"):
        reference_cli.capture("https://nada.test/", client=client)


def test_a_dark_site_and_a_site_with_a_motion_library_are_recognised() -> None:
    css = "body { background: #0A0A0B; color: #F4F4F5 } .btn { background: #38BDF8 }"

    dark = reference_cli.analyse_css(css, "<script src='/gsap.min.js'></script>")

    assert dark.surface == "dark" and dark.motion == 8


# --- skillui as a tool, not a dependency --------


def test_skillui_is_always_run_into_the_work_folder_and_without_a_skill(project: Paths) -> None:
    seen: list[list[str]] = []

    def run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        seen.append(command)
        assert kwargs["cwd"] == project.work / "reference" / "web"
        return subprocess.CompletedProcess(command, 0, "", "")

    out = reference_cli.run_skillui(
        project, "https://ejemplo.test", "web", ultra=True, which=lambda _: "/bin/skillui", run=run
    )

    command = seen[0]
    assert out == project.work / "reference" / "web"
    assert command[0] == "/bin/skillui" and command[command.index("--out") + 1] == str(out)
    for flag in ("--no-skill", "--url", "--name"):
        assert flag in command
    assert command[command.index("--format") + 1] == "design-md"
    assert command[command.index("--mode") + 1] == "ultra"
    assert str(project.root) not in command[command.index("--out") + 1].replace(str(out), "")


def test_without_skillui_the_message_names_the_alternative(project: Paths) -> None:
    with pytest.raises(DesignError, match=r"npm install -g skillui.*lee el CSS"):
        reference_cli.run_skillui(project, "https://x.test", "x", which=lambda _: None)


def test_a_skillui_failure_is_reported_with_its_last_line(project: Paths) -> None:
    def run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            command, 1, "", "cargando\nError: timeout en la página\n"
        )

    with pytest.raises(DesignError, match="skillui falló: Error: timeout en la página"):
        reference_cli.run_skillui(project, "https://x.test", "x", which=lambda _: "/s", run=run)


def test_skillui_output_is_read_from_its_folder(tmp_path: Path) -> None:
    (tmp_path / "tokens").mkdir()
    for name, data in (
        ("colors", SKILLUI_COLORS), ("typography", SKILLUI_TYPE), ("spacing", SKILLUI_SPACING)
    ):  # fmt: skip
        (tmp_path / "tokens" / f"{name}.json").write_text(json.dumps(data), encoding="utf-8")
    (tmp_path / "DESIGN.md").write_text(STITCH, encoding="utf-8")
    (tmp_path / "CLAUDE.md").write_text("ignore me", encoding="utf-8")

    brief = reference_cli.from_skillui_dir(tmp_path)

    assert brief.surface == "dark" and brief.motion == 8
    with pytest.raises(DesignError, match="no existe la carpeta"):
        reference_cli.from_skillui_dir(tmp_path / "nada")
    with pytest.raises(DesignError, match="colores ni fuentes"):
        (tmp_path / "vacia").mkdir()
        reference_cli.from_skillui_dir(tmp_path / "vacia")


# --- All the way: reference, proposal, apply, check --------


def settle(project: Paths, brief_name: str) -> list[str]:
    """Apply the proposal the way a person would, and return the errors design-check finds."""
    design_cli.apply_proposal(project, brief_name, force=True, client=fontsource())
    return [f.message for f in run_checks(project, allow_defaults=False) if f.level == "error"]


@pytest.fixture
def at_project(project: Paths, monkeypatch: pytest.MonkeyPatch) -> Paths:
    monkeypatch.setattr(reference_cli, "Paths", lambda: project)
    return project


def test_a_refero_export_goes_all_the_way(at_project: Paths, tmp_path: Path) -> None:
    source = tmp_path / "style.md"
    source.write_text(REFERO, encoding="utf-8")

    assert reference_cli.main(["--md", str(source), "--name", "aurora"]) == 0

    assert settle(at_project, "aurora") == []
    contract = load_contract(at_project.contract)
    assert contract.brand.primary == "#0F766E" and contract.brand.secondary == "#B45309"
    assert contract.brand.radius == "0.75rem" and contract.basecoat.theme == "maia"
    assert (
        contract.typography.display is not None and contract.typography.display.name == "Fraunces"
    )
    assert contract.typography.display.fallback == "serif"


def test_a_stitch_document_goes_all_the_way_and_what_could_not_be_mapped_is_recorded(
    at_project: Paths, tmp_path: Path
) -> None:
    source = tmp_path / "nocturne.md"
    source.write_text(STITCH, encoding="utf-8")
    at_project.design_md.write_text("# D\n", encoding="utf-8")
    # Level 8 needs Motion One on disk; `make design build` would download it. Not here.
    vendor = at_project.static / "js" / "vendor"
    vendor.mkdir(parents=True, exist_ok=True)
    (vendor / "motion.min.js").write_text("//", encoding="utf-8")

    assert reference_cli.main(["--md", str(source)]) == 0
    assert settle(at_project, "nocturne") == []

    contract = load_contract(at_project.contract)
    assert contract.brand.surface == "dark" and contract.brand.primary == "#38BDF8"
    # Space Grotesk is not a font Kiro vouches for: it became the catalogue's, and said so.
    assert contract.typography.display is not None
    assert contract.typography.display.name == "Public Sans"
    text = at_project.design_md.read_text(encoding="utf-8")
    assert "Space Grotesk → Public Sans" in text
    assert "nocturne.md" in text and "ni logos, ni imágenes" in text


def test_a_website_goes_all_the_way(at_project: Paths, monkeypatch: pytest.MonkeyPatch) -> None:
    real = reference_cli.capture
    monkeypatch.setattr(reference_cli, "capture", lambda url: real(url, client=site_client()))
    at_project.design_md.write_text("# D\n", encoding="utf-8")

    assert reference_cli.main(["--url", "https://casaverde.test/", "--name", "casa"]) == 0

    assert settle(at_project, "casa") == []
    assert load_contract(at_project.contract).brand.primary == "#166534"
    assert "https://casaverde.test/ (capturado el " in at_project.design_md.read_text("utf-8")


def test_a_skillui_folder_goes_all_the_way(at_project: Paths, tmp_path: Path) -> None:
    folder = tmp_path / "salida"
    (folder / "tokens").mkdir(parents=True)
    for name, data in (("colors", SKILLUI_COLORS), ("typography", SKILLUI_TYPE)):
        (folder / "tokens" / f"{name}.json").write_text(json.dumps(data), encoding="utf-8")

    assert reference_cli.main(["--skillui-dir", str(folder), "--name", "ui"]) == 0

    assert settle(at_project, "ui") == []
    assert load_contract(at_project.contract).brand.surface == "dark"


def test_a_reference_can_be_dressed_over_a_base(at_project: Paths, tmp_path: Path) -> None:
    base = tmp_path / "base.json"
    base.write_text(
        json.dumps(
            {
                "source": "advisor",
                "provenance": "uupm v2.15.0: fintech",
                "colours": [{"hex": "#1E3A8A", "role": "primary"}],
                "surface": "cream",
                "ux_notes": ["estados de carga con esqueleto"],
            }
        ),
        encoding="utf-8",
    )
    style = tmp_path / "s.md"
    style.write_text(STITCH, encoding="utf-8")

    assert reference_cli.main(["--md", str(style), "--base", str(base), "--name", "mix"]) == 0

    proposal = json.loads((at_project.proposals / "mix.json").read_text(encoding="utf-8"))
    assert proposal["inputs"] == ["advisor", "reference"]
    assert "estados de carga con esqueleto" in proposal["ux_notes"]


def test_the_command_line_reports_a_bad_input_without_a_traceback(
    at_project: Paths, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    empty = tmp_path / "x.md"
    empty.write_text("# Nada\n\nSolo texto.\n", encoding="utf-8")

    assert reference_cli.main(["--md", str(empty)]) == 1
    assert "error:" in capsys.readouterr().err
    assert reference_cli.main(["--md", str(tmp_path / "no-existe.md")]) == 1


def test_the_brief_schema_is_printable_for_a_free_text_brief(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert design_cli.main(["schema"]) == 0

    schema = json.loads(capsys.readouterr().out)
    assert {"source", "provenance", "colours", "fonts"} <= set(schema["properties"])
