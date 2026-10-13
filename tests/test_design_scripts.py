"""The I/O around the engine: build, fonts, shortcuts, vendoring and `design-check`.

Every test works in a temporary copy of the files the engine touches, with the
network replaced by `httpx2.MockTransport`: the real project and the real
Fontsource are never involved.
"""

from __future__ import annotations

import dataclasses
import hashlib
import re
import shutil
from pathlib import Path

import httpx2
import pytest
from scripts import design as design_cli
from scripts import font as font_cli
from scripts import motion as motion_cli
from scripts.brand import set_colors
from scripts.fetch import fetch_bytes

from app.branding import BrandError
from app.design_engine.blocks import remove_block
from app.design_engine.checks import Finding, run_checks
from app.design_engine.compiler import compile_contract
from app.design_engine.contract import (
    DesignContract,
    DesignError,
    dump_contract,
    load_contract,
    parse_contract,
)
from app.design_engine.paths import Paths
from app.design_engine.presets import PRESETS
from tests.test_design_engine import make_woff2

REPO = Path(__file__).resolve().parent.parent


# --- Fixtures ---------------------------------------------------------------


def pristine_css(path: Path) -> str:
    """The framework's `input.css` as it ships, whatever this project compiled into its own.

    A configured project has `kiro:*` blocks in `input.css`; the tests need the
    unconfigured starting point so that they do not depend on the project's identity.
    """
    css = path.read_text(encoding="utf-8")
    css = remove_block(css, "brand")
    css = remove_block(css, "fonts")
    return re.sub(
        r"/\* kiro:theme:start.*?kiro:theme:end \*/",
        '@import "./vendor/basecoat/basecoat-vega.css";',
        css,
        flags=re.DOTALL,
    )


@pytest.fixture
def project(tmp_path: Path) -> Paths:
    """The slice of a Kiro project the engine reads, copied into a temp dir."""
    paths = Paths(tmp_path)
    (paths.static / "css" / "vendor" / "basecoat").mkdir(parents=True)
    paths.css.write_text(pristine_css(REPO / "app/static/css/input.css"), encoding="utf-8")
    for theme in ("vega", "nova", "maia", "lyra", "mira", "luma", "sera", "rhea"):
        (paths.basecoat / f"basecoat-{theme}.css").write_text("/* theme */")
    shutil.copytree(REPO / "app/templates/partials/headers", paths.headers)
    (paths.static / "js").mkdir(parents=True)
    for name in ("motion.js", "motion-lib.js", "motion-gsap.js"):
        shutil.copy(REPO / "app/static/js" / name, paths.static / "js" / name)
    paths.contract.write_text(dump_contract(DesignContract()), encoding="utf-8")
    return paths


def fontsource(requests: list[str] | None = None) -> httpx2.Client:
    """A Fontsource that serves a valid woff2 for any `latin-<weight>-normal` request."""

    def handler(request: httpx2.Request) -> httpx2.Response:
        if requests is not None:
            requests.append(str(request.url))
        if "/fontsource/fonts/" in str(request.url):
            if "nonexistent" in str(request.url):
                return httpx2.Response(404)
            return httpx2.Response(200, content=make_woff2())
        return httpx2.Response(404)

    return httpx2.Client(transport=httpx2.MockTransport(handler))


def set_contract(paths: Paths, contract: DesignContract) -> None:
    paths.contract.write_text(dump_contract(contract), encoding="utf-8")


# --- fetch ------------------------------------------------------------------


def test_fetch_returns_the_body() -> None:
    client = httpx2.Client(
        transport=httpx2.MockTransport(lambda r: httpx2.Response(200, content=b"abc"))
    )

    assert fetch_bytes("https://x.test/a", limit=100, label="a", client=client) == b"abc"


def test_fetch_refuses_more_than_the_limit() -> None:
    client = httpx2.Client(
        transport=httpx2.MockTransport(lambda r: httpx2.Response(200, content=b"x" * 5000))
    )

    with pytest.raises(DesignError, match="pesa más de"):
        fetch_bytes("https://x.test/a", limit=1000, label="a", client=client)


def test_fetch_says_when_the_file_does_not_exist() -> None:
    client = httpx2.Client(transport=httpx2.MockTransport(lambda r: httpx2.Response(404)))

    with pytest.raises(DesignError, match="no existe en el origen"):
        fetch_bytes("https://x.test/a", limit=100, label="Fraunces 400", client=client)


def test_fetch_turns_network_failures_into_messages() -> None:
    def boom(request: httpx2.Request) -> httpx2.Response:
        raise httpx2.ConnectError("sin red", request=request)

    client = httpx2.Client(transport=httpx2.MockTransport(boom))

    with pytest.raises(DesignError, match="no pude descargar"):
        fetch_bytes("https://x.test/a", limit=100, label="a", client=client)


# --- build ------------------------------------------------------------------


def test_build_applies_the_contract_and_downloads_fonts(project: Paths) -> None:
    set_contract(project, PRESETS["minimalista"].contract)
    asked: list[str] = []

    report = design_cli.build(project, client=fontsource(asked))

    css = project.css.read_text(encoding="utf-8")
    assert report.changed
    assert "kiro:brand:start" in css and "kiro:fonts:start" in css and "kiro:theme:start" in css
    assert 'basecoat-nova.css"' in css
    assert sorted(p.name for p in project.fonts.glob("*.woff2")) == [
        "geist-latin-400-normal.woff2",
        "geist-latin-600-normal.woff2",
        "newsreader-latin-400-normal.woff2",
        "newsreader-latin-600-normal.woff2",
    ]
    assert len(asked) == 4
    assert all("cdn.jsdelivr.net/fontsource/fonts/" in url for url in asked)


def test_build_is_idempotent_and_does_not_redownload(project: Paths) -> None:
    set_contract(project, PRESETS["minimalista"].contract)
    design_cli.build(project, client=fontsource())
    first = project.css.read_text(encoding="utf-8")
    asked: list[str] = []

    report = design_cli.build(project, client=fontsource(asked))

    assert not report.changed
    assert project.css.read_text(encoding="utf-8") == first
    assert asked == [], "una fuente válida en disco no se vuelve a bajar (funciona sin red)"
    assert report.downloaded == ()


def test_build_replaces_a_corrupt_font(project: Paths) -> None:
    set_contract(project, PRESETS["panel-de-datos"].contract)
    design_cli.build(project, client=fontsource())
    victim = next(project.fonts.glob("*.woff2"))
    victim.write_bytes(b"<html>not a font")

    report = design_cli.build(project, client=fontsource())

    assert victim.name in report.downloaded
    assert victim.read_bytes()[:4] == b"wOF2"


def test_a_failed_download_leaves_input_css_untouched(project: Paths) -> None:
    """`input.css` must never point at fonts that are not there."""
    before = project.css.read_text(encoding="utf-8")
    contract = DesignContract.model_validate(
        {"type": {"body": {"name": "Nonexistent Font", "weights": [400]}}}
    )
    set_contract(project, contract)

    with pytest.raises(DesignError, match="no existe"):
        design_cli.build(project, client=fontsource())

    assert project.css.read_text(encoding="utf-8") == before
    assert not project.fonts.exists() or not list(project.fonts.glob("*"))


def test_a_font_that_is_not_a_woff2_is_not_installed(project: Paths) -> None:
    html = httpx2.Client(
        transport=httpx2.MockTransport(
            lambda r: httpx2.Response(200, content=b"<html>" + b"x" * 2000)
        )
    )
    set_contract(project, PRESETS["panel-de-datos"].contract)

    with pytest.raises(DesignError, match="no es un woff2"):
        design_cli.build(project, client=html)

    assert not project.fonts.exists() or not list(project.fonts.glob("*.woff2"))


def test_build_needs_a_contract(project: Paths) -> None:
    project.contract.unlink()

    with pytest.raises(DesignError, match="make design init"):
        design_cli.build(project)


def test_build_checks_the_header_partial_exists(project: Paths) -> None:
    contract = DesignContract.model_validate({"structure": {"header": "floating-pill"}})
    set_contract(project, contract)
    (project.headers / "floating-pill.html").unlink()

    with pytest.raises(DesignError, match="floating-pill"):
        design_cli.build(project)


def test_build_with_a_failing_palette_writes_nothing(project: Paths) -> None:
    before = project.css.read_text(encoding="utf-8")
    set_contract(project, DesignContract.model_validate({"brand": {"primary": "#E11D48"}}))

    with pytest.raises(DesignError, match="WCAG"):
        design_cli.build(project)

    assert project.css.read_text(encoding="utf-8") == before


def test_a_project_can_keep_its_own_css_next_to_the_blocks(project: Paths) -> None:
    project.css.write_text(project.css.read_text() + "\n.mi-clase { color: red; }\n")
    set_contract(project, DesignContract.model_validate({"brand": {"primary": "#0F766E"}}))

    design_cli.build(project)
    design_cli.build(project)

    assert ".mi-clase { color: red; }" in project.css.read_text()


# --- init / set -------------------------------------------------------------


def test_init_writes_a_preset(project: Paths) -> None:
    design_cli.init(project, preset="brutalista", primary=None, force=False)

    contract = load_contract(project.contract)
    assert contract == PRESETS["brutalista"].contract


def test_init_can_override_the_primary(project: Paths) -> None:
    design_cli.init(project, preset="institucional", primary="#0f766e", force=False)

    assert load_contract(project.contract).brand.primary == "#0F766E"
    assert load_contract(project.contract).basecoat.theme == "vega"


def test_init_does_not_clobber_a_chosen_identity(project: Paths) -> None:
    design_cli.init(project, preset="brutalista", primary=None, force=False)

    with pytest.raises(DesignError, match="--force"):
        design_cli.init(project, preset="expresivo", primary=None, force=False)

    design_cli.init(project, preset="expresivo", primary=None, force=True)
    assert load_contract(project.contract).basecoat.theme == "rhea"


def test_init_over_the_default_contract_needs_no_force(project: Paths) -> None:
    design_cli.init(project, preset="minimalista", primary=None, force=False)

    assert not load_contract(project.contract).is_default


def test_set_edits_one_value_and_validates_the_whole(project: Paths) -> None:
    design_cli.set_values(project, ["basecoat.theme=rhea", "motion.level=6", "brand.radius=0"])

    contract = load_contract(project.contract)
    assert contract.basecoat.theme == "rhea"
    assert contract.motion.level == 6
    assert contract.brand.radius == "0rem"


@pytest.mark.parametrize(
    ("assignment", "fragment"),
    [
        ("theme=rhea", "seccion.clave"),
        ("basecoat.nope=1", "no existe"),
        ("type.body=Inter", "make font"),
        ("nada.theme=x", "no se edita así"),
        ("basecoat.theme=bootstrap", "vega | nova"),
        ("motion.level=99", "como mucho 10"),
    ],
)
def test_set_rejects_what_it_cannot_apply(project: Paths, assignment: str, fragment: str) -> None:
    before = project.contract.read_text(encoding="utf-8")

    with pytest.raises(DesignError, match=fragment):
        design_cli.set_values(project, [assignment])

    assert project.contract.read_text(encoding="utf-8") == before


# --- brand-colors shortcut --------------------------------------------------


def test_brand_colors_writes_the_toml_and_rebuilds(
    project: Paths, capsys: pytest.CaptureFixture[str]
) -> None:
    set_colors(
        "#0f766e", radius="0.25rem", neutral="warm", surface="cream", secondary=None, paths=project
    )

    contract = load_contract(project.contract)
    assert contract.brand.primary == "#0F766E"
    assert contract.brand.neutral == "warm"
    assert contract.brand.surface == "cream"
    css = project.css.read_text(encoding="utf-8")
    assert "--radius: 0.25rem;" in css
    assert "contraste del botón primario, modo claro" in capsys.readouterr().out


def test_brand_colors_keeps_what_it_was_not_asked_to_change(project: Paths) -> None:
    set_colors("#0F766E", radius=None, neutral="cool", surface=None, secondary=None, paths=project)
    set_colors("#C2410C", radius=None, neutral=None, surface=None, secondary=None, paths=project)

    contract = load_contract(project.contract)
    assert contract.brand.primary == "#C2410C"
    assert contract.brand.neutral == "cool"


def test_brand_colors_can_clear_the_secondary(project: Paths) -> None:
    set_colors(
        "#C2410C", radius=None, neutral=None, surface=None, secondary="#1E3A5F", paths=project
    )
    assert load_contract(project.contract).brand.secondary == "#1E3A5F"

    set_colors("#C2410C", radius=None, neutral=None, surface=None, secondary="", paths=project)
    assert load_contract(project.contract).brand.secondary is None


def test_brand_colors_with_an_unreadable_colour_fails_with_a_fix(project: Paths) -> None:
    with pytest.raises(BrandError, match="Prueba #"):
        set_colors(
            "#E11D48", radius=None, neutral=None, surface=None, secondary=None, paths=project
        )


# --- make font --------------------------------------------------------------


def fontsource_api(payload: dict[str, object] | None, status: int = 200) -> httpx2.Client:
    def handler(request: httpx2.Request) -> httpx2.Response:
        if payload is None:
            raise httpx2.ConnectError("sin red", request=request)
        return httpx2.Response(status, json=payload)

    return httpx2.Client(transport=httpx2.MockTransport(handler))


FRAUNCES = {
    "id": "fraunces",
    "category": "serif",
    "weights": [400, 600, 700],
    "subsets": ["latin", "latin-ext"],
}


def test_adding_a_font_records_it_and_infers_the_fallback() -> None:
    contract, notes = font_cli.add_font(
        DesignContract(),
        "display",
        "Fraunces",
        [400, 700],
        fallback=None,
        client=fontsource_api(FRAUNCES),
    )

    assert contract.typography.display is not None
    assert contract.typography.display.weights == (400, 700)
    assert contract.typography.display.fallback == "serif"
    assert any("serif" in note for note in notes)


def test_a_mono_family_in_the_mono_role_needs_no_fallback_note() -> None:
    info = {**FRAUNCES, "id": "jetbrains-mono", "category": "monospace"}

    contract, notes = font_cli.add_font(
        DesignContract(),
        "mono",
        "JetBrains Mono",
        [400],
        fallback=None,
        client=fontsource_api(info),
    )

    assert contract.typography.mono is not None
    assert contract.typography.mono.fallback is None  # `mono` is already the role's default
    assert notes == []


def test_an_explicit_fallback_wins_over_the_inferred_one() -> None:
    contract, _ = font_cli.add_font(
        DesignContract(),
        "display",
        "Fraunces",
        [400],
        fallback="sans",
        client=fontsource_api(FRAUNCES),
    )

    assert contract.typography.display is not None
    assert contract.typography.display.fallback == "sans"


def test_weights_the_family_does_not_have_are_listed() -> None:
    with pytest.raises(DesignError, match="disponibles: 400, 600, 700"):
        font_cli.add_font(
            DesignContract(),
            "body",
            "Fraunces",
            [400, 300],
            fallback=None,
            client=fontsource_api(FRAUNCES),
        )


def test_a_family_missing_from_fontsource_mentions_fontshare() -> None:
    with pytest.raises(DesignError, match="Fontshare"):
        font_cli.add_font(
            DesignContract(),
            "body",
            "Satoshi",
            [400],
            fallback=None,
            client=fontsource_api({}, 404),
        )


def test_an_unreachable_api_does_not_block_adding_a_font() -> None:
    contract, notes = font_cli.add_font(
        DesignContract(), "body", "Inter", [400], fallback=None, client=fontsource_api(None)
    )

    assert contract.typography.body is not None
    assert any("Fontsource" in note for note in notes)


def test_a_family_without_the_latin_subset_is_refused() -> None:
    info = {**FRAUNCES, "subsets": ["cyrillic"]}

    with pytest.raises(DesignError, match="latin"):
        font_cli.add_font(
            DesignContract(), "body", "Fraunces", [400], fallback=None, client=fontsource_api(info)
        )


@pytest.mark.parametrize(
    ("weights", "fragment"),
    [([450], "peso"), ([], "pesos"), ([0], "peso")],
)
def test_malformed_weights_read_like_a_bad_design_toml(weights: list[int], fragment: str) -> None:
    with pytest.raises(DesignError, match=fragment):
        font_cli.add_font(
            DesignContract(), "body", "Inter", weights, fallback=None, client=fontsource_api(None)
        )


def test_the_font_command_reports_unparseable_weights(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    code = font_cli.main(["--name", "Inter", "--weights", "regular", "--role", "body"])

    assert code == 1
    assert "lista de números" in capsys.readouterr().err


def test_an_unknown_role_is_refused() -> None:
    with pytest.raises(DesignError, match="role"):
        font_cli.add_font(
            DesignContract(), "title", "Inter", [400], fallback=None, client=fontsource_api(None)
        )


# --- Vendoring motion libraries --------------------------------------------


def fake_library(payload: bytes, *, digest: str | None = None) -> motion_cli.Library:
    return motion_cli.Library(
        key="motion",
        title="Fake",
        version="1.0.0",
        license_name="MIT",
        license_url="https://example.test/license",
        notes="nota",
        files=(
            motion_cli.VendorFile(
                "https://cdn.test/fake.min.js",
                "js/vendor/fake.min.js",
                digest or hashlib.sha256(payload).hexdigest(),
            ),
        ),
    )


def test_a_library_is_installed_when_its_hash_matches(tmp_path: Path) -> None:
    payload = b"/* lib */ " * 10
    client = httpx2.Client(
        transport=httpx2.MockTransport(lambda r: httpx2.Response(200, content=payload))
    )

    written = motion_cli.vendor_library(fake_library(payload), tmp_path, client=client)

    assert written == ("js/vendor/fake.min.js",)
    assert (tmp_path / "js/vendor/fake.min.js").read_bytes() == payload


def test_a_file_that_does_not_match_its_pinned_hash_is_never_written(tmp_path: Path) -> None:
    client = httpx2.Client(
        transport=httpx2.MockTransport(lambda r: httpx2.Response(200, content=b"tampered"))
    )

    with pytest.raises(DesignError, match="distinto del esperado"):
        motion_cli.vendor_library(fake_library(b"original"), tmp_path, client=client)

    assert not (tmp_path / "js/vendor/fake.min.js").exists()


def test_an_installed_and_verified_library_is_not_downloaded_again(tmp_path: Path) -> None:
    payload = b"lib"
    target = tmp_path / "js/vendor/fake.min.js"
    target.parent.mkdir(parents=True)
    target.write_bytes(payload)
    calls: list[str] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        calls.append(str(request.url))
        return httpx2.Response(200, content=payload)

    written = motion_cli.vendor_library(
        fake_library(payload),
        tmp_path,
        client=httpx2.Client(transport=httpx2.MockTransport(handler)),
    )

    assert written == () and calls == []


def test_a_tampered_local_copy_is_replaced(tmp_path: Path) -> None:
    payload = b"the real thing"
    target = tmp_path / "js/vendor/fake.min.js"
    target.parent.mkdir(parents=True)
    target.write_bytes(b"edited by hand")
    client = httpx2.Client(
        transport=httpx2.MockTransport(lambda r: httpx2.Response(200, content=payload))
    )

    motion_cli.vendor_library(fake_library(payload), tmp_path, client=client)

    assert target.read_bytes() == payload


def test_the_pinned_libraries_are_the_ones_the_levels_expect() -> None:
    for key, library in motion_cli.LIBRARIES.items():
        assert library.version.count(".") == 2
        assert all(len(f.sha256) == 64 for f in library.files)
        assert all(f"@{library.version}/" in f.url for f in library.files), "versión sin fijar"
        assert {f.dest for f in library.files} <= {
            "js/vendor/motion.min.js",
            "js/vendor/gsap.min.js",
            "js/vendor/ScrollTrigger.min.js",
        }
        assert key in {"motion", "gsap"}
    assert motion_cli.library_for_level(3) is None
    assert motion_cli.library_for_level(5) is None
    assert motion_cli.library_for_level(8) is motion_cli.LIBRARIES["motion"]
    assert motion_cli.library_for_level(9) is motion_cli.LIBRARIES["gsap"]


def test_the_notice_names_the_licence_of_what_is_installed(tmp_path: Path) -> None:
    for library in motion_cli.LIBRARIES.values():
        for file in library.files:
            target = tmp_path / file.dest
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("//")

    notice = motion_cli.render_notice(tmp_path)

    assert notice is not None
    assert "GSAP Standard 'no charge' license" in notice
    assert "https://gsap.com/standard-license" in notice
    assert "Webflow" in notice  # the restriction that matters is stated, not buried
    assert "no los redistribuye" in notice
    assert "MIT" in notice


def test_no_notice_without_libraries(tmp_path: Path) -> None:
    assert motion_cli.render_notice(tmp_path) is None


def test_build_vendors_what_the_motion_level_needs(
    project: Paths, monkeypatch: pytest.MonkeyPatch
) -> None:
    set_contract(project, DesignContract.model_validate({"motion": {"level": 8}}))
    payload = b"//motion"
    real = motion_cli.LIBRARIES["motion"]
    # A library whose pinned hash is that of our fake payload: same code path, no network.
    fake = dataclasses.replace(
        real,
        files=(
            motion_cli.VendorFile(
                real.files[0].url, real.files[0].dest, hashlib.sha256(payload).hexdigest()
            ),
        ),
    )
    monkeypatch.setitem(motion_cli.LIBRARIES, "motion", fake)
    client = httpx2.Client(
        transport=httpx2.MockTransport(lambda r: httpx2.Response(200, content=payload))
    )

    report = design_cli.build(project, client=client)

    assert "js/vendor/motion.min.js" in report.downloaded
    assert (project.static / "js/vendor/motion.min.js").read_bytes() == payload
    assert (project.static / "js/vendor/NOTICE.md").is_file()


def test_build_fails_when_a_script_of_the_framework_itself_is_missing(project: Paths) -> None:
    """A missing `motion.js` is an incomplete upgrade, not something to download."""
    set_contract(project, DesignContract.model_validate({"motion": {"level": 5}}))
    (project.static / "js" / "motion.js").unlink()
    before = project.css.read_text(encoding="utf-8")

    with pytest.raises(DesignError, match=r"js/motion\.js.*viene con el framework"):
        design_cli.build(project)

    assert project.css.read_text(encoding="utf-8") == before


def test_build_at_a_level_that_needs_no_library_downloads_nothing(project: Paths) -> None:
    set_contract(project, DesignContract.model_validate({"motion": {"level": 5}}))

    def refuse(request: httpx2.Request) -> httpx2.Response:
        raise AssertionError("no debería salir a la red")

    report = design_cli.build(project, client=httpx2.Client(transport=httpx2.MockTransport(refuse)))

    assert report.downloaded == ()


# --- design-check -----------------------------------------------------------


def levels(findings: list[Finding]) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {"ok": [], "warn": [], "error": []}
    for finding in findings:
        out[finding.level].append(finding.message)
    return out


def test_check_needs_a_contract(tmp_path: Path) -> None:
    result = levels(run_checks(Paths(tmp_path)))

    assert result["error"] == ["no existe design.toml"]


def test_check_reports_an_invalid_contract(project: Paths) -> None:
    project.contract.write_text('[brand]\nprimary = "x"', encoding="utf-8")

    result = levels(run_checks(project))

    assert any("brand.primary" in message for message in result["error"])


def test_the_default_contract_is_flagged_as_potential_convergence(project: Paths) -> None:
    result = levels(run_checks(project))

    assert any("valores por defecto" in message for message in result["error"])
    assert not any("al día" in message for message in result["error"]), (
        "el estado de fábrica está al día"
    )


def test_defaults_can_be_accepted_on_purpose(project: Paths) -> None:
    result = levels(run_checks(project, allow_defaults=True))

    assert result["error"] == []
    assert any("valores por defecto" in message for message in result["warn"])


def test_a_built_preset_passes_the_check(project: Paths) -> None:
    set_contract(project, PRESETS["panel-de-datos"].contract)
    design_cli.build(project, client=fontsource())

    result = levels(run_checks(project))

    assert result["error"] == [], result["error"]
    assert any("al día" in message for message in result["ok"])
    assert any("contraste AA" in message for message in result["ok"])


def test_check_catches_a_toml_edited_but_not_built(project: Paths) -> None:
    set_contract(project, PRESETS["minimalista"].contract)
    design_cli.build(project, client=fontsource())
    set_contract(project, PRESETS["brutalista"].contract)

    result = levels(run_checks(project))

    assert any("no está al día" in message for message in result["error"])


def test_check_catches_a_deleted_font(project: Paths) -> None:
    set_contract(project, PRESETS["panel-de-datos"].contract)
    design_cli.build(project, client=fontsource())
    next(project.fonts.glob("*.woff2")).unlink()

    result = levels(run_checks(project))

    assert any("falta la fuente" in message for message in result["error"])


def test_check_catches_a_corrupt_font(project: Paths) -> None:
    set_contract(project, PRESETS["panel-de-datos"].contract)
    design_cli.build(project, client=fontsource())
    next(project.fonts.glob("*.woff2")).write_bytes(b"x" * 2000)

    result = levels(run_checks(project))

    assert any("woff2" in message for message in result["error"])


def test_check_warns_about_orphan_fonts(project: Paths) -> None:
    set_contract(project, PRESETS["panel-de-datos"].contract)
    design_cli.build(project, client=fontsource())
    (project.fonts / "old-latin-400-normal.woff2").write_bytes(make_woff2())

    result = levels(run_checks(project))

    assert any("huérfana" in message and "old-latin" in message for message in result["warn"])


def test_check_catches_a_motion_level_without_its_files(project: Paths) -> None:
    set_contract(project, DesignContract.model_validate({"motion": {"level": 9}}))
    # Compile without `build`, which would try to download GSAP.
    css = project.css.read_text(encoding="utf-8")
    project.css.write_text(
        compile_contract(load_contract(project.contract), css).css, encoding="utf-8"
    )

    result = levels(run_checks(project))

    assert any("gsap.min.js" in message for message in result["error"])


def test_check_flags_motion_attributes_the_level_cannot_run(project: Paths) -> None:
    set_contract(project, DesignContract.model_validate({"motion": {"level": 5}}))
    design_cli.build(project)
    pages = project.templates / "pages"
    pages.mkdir(parents=True)
    (pages / "landing.html").write_text(
        '<h1 data-motion="split-reveal">a</h1><div data-motion="pin"></div>'
        '<div data-motion="levitate"></div><p data-motion-ease="spring" data-motion="reveal"></p>',
        encoding="utf-8",
    )

    warnings = levels(run_checks(project))["warn"]

    assert any('"pin"' in w and "motion.level >= 9" in w for w in warnings), warnings
    assert any('"levitate"' in w and "no existe" in w for w in warnings)
    assert any("spring" in w for w in warnings)
    assert not any("split-reveal" in w for w in warnings), "el nivel 5 sí entiende split-reveal"


def test_check_ignores_vendored_and_email_templates(project: Paths) -> None:
    set_contract(project, DesignContract.model_validate({"motion": {"level": 5}}))
    design_cli.build(project)
    for folder in ("basecoat", "emails"):
        (project.templates / folder).mkdir(parents=True)
        (project.templates / folder / "x.html").write_text('<i data-motion="pin"></i>')

    assert not any("pin" in w for w in levels(run_checks(project))["warn"])


def test_check_ignores_attributes_that_only_appear_in_comments(project: Paths) -> None:
    set_contract(project, DesignContract.model_validate({"motion": {"level": 5}}))
    design_cli.build(project)
    pages = project.templates / "pages"
    pages.mkdir(parents=True)
    (pages / "doc.html").write_text(
        '{# Uso: <div data-motion="pin"> pide nivel 9 #}<p data-motion="reveal">hola</p>',
        encoding="utf-8",
    )

    assert not any("pin" in w for w in levels(run_checks(project))["warn"])


def test_check_skips_the_design_showcase_that_gates_by_level_itself(project: Paths) -> None:
    set_contract(project, DesignContract.model_validate({"motion": {"level": 5}}))
    design_cli.build(project)
    (project.templates / "pages").mkdir(parents=True)
    (project.templates / "pages" / "design.html").write_text('<i data-motion="pin"></i>')

    assert not any("pin" in w for w in levels(run_checks(project))["warn"])


def test_check_compares_design_md_with_the_contract(project: Paths) -> None:
    set_contract(
        project,
        DesignContract.model_validate({"brand": {"primary": "#0F766E"}, "motion": {"level": 5}}),
    )
    design_cli.build(project)
    project.design_md.write_text(
        "## Los tres diales\n| `MOTION_INTENSITY` | 8 | a | b |\n"
        "- **Primario (acento de marca):** #C2410C\n",
        encoding="utf-8",
    )

    warnings = levels(run_checks(project))["warn"]

    assert any("MOTION_INTENSITY = 8" in w and "motion.level = 5" in w for w in warnings)
    assert any("#C2410C" in w and "#0F766E" in w for w in warnings)
    assert any("firma visual" in w for w in warnings)


def test_check_accepts_a_coherent_design_md(project: Paths) -> None:
    set_contract(
        project,
        DesignContract.model_validate({"brand": {"primary": "#0f6"}, "motion": {"level": 5}}),
    )
    design_cli.build(project)
    project.design_md.write_text(
        "## Los tres diales\n| `MOTION_INTENSITY` | 5 | a | b |\n"
        "- **Primario (acento de marca):** #0f6\n\n## Firma visual\n- Titulares enormes.\n",
        encoding="utf-8",
    )

    result = levels(run_checks(project))

    assert result["error"] == []
    assert any("coherente" in message for message in result["ok"])


def test_check_says_when_design_md_is_unfinished(project: Paths) -> None:
    project.design_md.write_text("- **Estilo:** TODO", encoding="utf-8")

    assert any("TODO" in w for w in levels(run_checks(project))["warn"])


def test_check_exit_code_follows_the_errors(
    project: Paths, capsys: pytest.CaptureFixture[str]
) -> None:
    assert design_cli.check(project, allow_defaults=False) == 1
    assert design_cli.check(project, allow_defaults=True) == 0
    assert "errores" in capsys.readouterr().out


# --- command line -----------------------------------------------------------


def test_the_cli_reports_errors_without_a_traceback(
    project: Paths, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(design_cli, "Paths", lambda: project)
    project.contract.write_text('[brand]\nprimary = "x"', encoding="utf-8")

    code = design_cli.main(["build"])

    assert code == 1
    assert "design.toml tiene 1 error" in capsys.readouterr().err


def test_the_cli_can_init_and_build_end_to_end(
    project: Paths, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(design_cli, "Paths", lambda: project)
    monkeypatch.setattr(design_cli, "fetch_bytes", lambda url, **kw: make_woff2())

    code = design_cli.main(["init", "--preset", "minimalista"])

    out = capsys.readouterr().out
    assert code == 0
    assert "estilo 'minimalista'" in out
    assert "fuente display: Newsreader" in out
    assert parse_contract(project.contract.read_text()).basecoat.theme == "nova"
    assert "kiro:fonts:start" in project.css.read_text()
