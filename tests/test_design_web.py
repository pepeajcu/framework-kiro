"""The design engine as the browser meets it: layouts, headers, motion hooks, `/_design`.

Pages are rendered through the real app. What the engine decides at request time
(`design.header`, dark surface, motion scripts) is swapped with a plain
`DesignRuntime`, so each archetype can be asserted without touching `design.toml`.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Callable, Generator
from pathlib import Path

import pytest
from fastapi import Request
from fastapi.responses import HTMLResponse
from fastapi.testclient import TestClient
from jinja2 import ChoiceLoader, FileSystemLoader
from sqlalchemy.orm import Session

from app.config import Environment, get_settings
from app.deps import OptionalUser
from app.design_engine.contract import (
    HEADERS,
    DesignContract,
    dump_contract,
)
from app.design_engine.paths import Paths
from app.design_engine.presets import PRESETS
from app.design_engine.runtime import DesignProxy, DesignRuntime, runtime_from_contract
from app.main import create_app
from app.models.user import User
from app.services import design as design_service
from app.templating import render, templates
from tests.conftest import PASSWORD, override_dependencies
from tests.test_design_engine import make_woff2

UseDesign = Callable[..., DesignRuntime]


@pytest.fixture
def use_design(monkeypatch: pytest.MonkeyPatch) -> UseDesign:
    """Replace the `design` template global for one test."""

    def apply(**fields: object) -> DesignRuntime:
        runtime = DesignRuntime(**fields)  # type: ignore[arg-type]
        monkeypatch.setitem(templates.env.globals, "design", runtime)
        return runtime

    return apply


LANDING = (
    '{% extends "layouts/landing.html" %}{% block title %}t{% endblock %}'
    '{% block content %}<p id="c">hola</p>{% endblock %}'
)
APP = (
    '{% extends "layouts/app.html" %}{% block title %}t{% endblock %}'
    '{% block content %}<p id="c">hola</p>{% endblock %}'
)


@pytest.fixture
def pages(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    db_session: Session,
    mailbox: object,
) -> Generator[TestClient, None, None]:
    """An app with two throwaway pages, one per layout.

    The layouts and headers are what is under test, so they are rendered through
    pages of the test's own rather than through the project's home page: that one
    is the first thing a project replaces.
    """
    (tmp_path / "kiro_test_landing.html").write_text(LANDING, encoding="utf-8")
    (tmp_path / "kiro_test_app.html").write_text(APP, encoding="utf-8")
    monkeypatch.setattr(
        templates.env, "loader", ChoiceLoader([FileSystemLoader(tmp_path), templates.env.loader])
    )
    app = create_app(enforce_csrf=False)

    @app.get("/_t/landing", response_class=HTMLResponse)
    def landing(request: Request, user: OptionalUser) -> HTMLResponse:
        return render(request, "kiro_test_landing.html")

    @app.get("/_t/app", response_class=HTMLResponse)
    def application(request: Request, user: OptionalUser) -> HTMLResponse:
        return render(request, "kiro_test_app.html")

    override_dependencies(app, db_session, mailbox)  # type: ignore[arg-type]
    with TestClient(app, follow_redirects=False) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def pages_logged_in(pages: TestClient, user: User) -> TestClient:
    response = pages.post("/login", data={"email": user.email, "password": PASSWORD})
    assert response.status_code == 303
    return pages


def between(html: str, start: str, end: str) -> str:
    return html.split(start, 1)[1].split(end, 1)[0]


# --- Layouts ----------------------------------------------------------------


def test_the_landing_layout_runs_to_the_edge(pages: TestClient) -> None:
    html = pages.get("/_t/landing").text

    assert "max-w-6xl" in between(html, "<header", "</header>")
    assert "max-w-6xl" in between(html, "<footer", "</footer>")
    assert '<main id="main">' in html, "una landing no encierra el contenido en un contenedor"


def test_the_app_layout_keeps_the_narrow_container(pages: TestClient) -> None:
    html = pages.get("/_t/app").text

    assert "max-w-5xl" in re.search(r"<main[^>]*>", html).group(0)  # type: ignore[union-attr]
    assert "max-w-5xl" in between(html, "<header", "</header>")
    assert "max-w-5xl" in between(html, "<footer", "</footer>")
    assert "max-w-6xl" not in html


def test_auth_pages_and_errors_use_the_app_layout(client: TestClient) -> None:
    for path in ("/login", "/register", "/forgot-password", "/no-existe"):
        html = client.get(path).text
        assert "max-w-5xl" in re.search(r"<main[^>]*>", html).group(0), path  # type: ignore[union-attr]


# --- Header archetypes ------------------------------------------------------

DISTINCTIVE = {
    "sticky-blur": "backdrop-blur",
    "floating-pill": "rounded-full",
    "industrial-rule": "border-b-2",
    "terminal-bar": "bg-foreground text-background",
    "custom": "backdrop-blur",
}


def test_every_archetype_has_a_marker_in_this_test() -> None:
    assert set(DISTINCTIVE) == set(HEADERS)


@pytest.mark.parametrize("header", HEADERS)
def test_each_header_archetype_renders_with_its_own_shape(
    pages: TestClient, use_design: UseDesign, header: str
) -> None:
    use_design(header=header)

    html = pages.get("/_t/landing").text
    bar = between(html, "<header", "</header>")

    assert DISTINCTIVE[header] in bar
    assert 'aria-label="Principal"' in bar


@pytest.mark.parametrize("header", HEADERS)
def test_session_logic_survives_every_archetype(
    pages_logged_in: TestClient, use_design: UseDesign, header: str, user: User
) -> None:
    """Rewriting the visual header must never break logout (it is a POST with CSRF)."""
    use_design(header=header)

    bar = between(pages_logged_in.get("/_t/landing").text, "<header", "</header>")

    assert user.email in bar
    assert 'action="/logout"' in bar and 'method="post"' in bar
    assert 'name="csrf_token"' in between(bar, 'action="/logout"', "</form>")
    assert "Salir" in bar and "Notas" in bar


@pytest.mark.parametrize("header", HEADERS)
def test_anonymous_visitors_get_the_login_links_in_every_archetype(
    pages: TestClient, use_design: UseDesign, header: str
) -> None:
    use_design(header=header)

    bar = between(pages.get("/_t/landing").text, "<header", "</header>")

    assert 'href="/login"' in bar and "Entrar" in bar
    assert 'href="/register"' in bar and "Crear cuenta" in bar
    assert "Salir" not in bar


def test_an_unknown_header_falls_back_instead_of_breaking_the_site(
    pages: TestClient, use_design: UseDesign
) -> None:
    use_design(header="does-not-exist")

    response = pages.get("/_t/landing")

    assert response.status_code == 200
    assert "backdrop-blur" in between(response.text, "<header", "</header>")


def test_the_terminal_bar_uses_outline_buttons_to_stay_readable(
    pages: TestClient, use_design: UseDesign
) -> None:
    """Ghost buttons would vanish on an inverted bar."""
    use_design(header="terminal-bar")

    bar = between(pages.get("/_t/landing").text, "<header", "</header>")

    assert 'data-variant="outline"' in bar
    assert 'data-variant="ghost"' not in bar


def test_the_terminal_bar_is_not_a_white_strip_on_a_dark_site(
    pages: TestClient, use_design: UseDesign
) -> None:
    """Inverting foreground and background on a dark surface paints a light bar."""
    use_design(header="terminal-bar", dark=True)

    bar = between(pages.get("/_t/landing").text, "<header", "</header>")

    assert "dark:bg-card" in bar and "dark:text-foreground" in bar and "dark:border-b" in bar


def test_the_brand_mark_inherits_its_colour_from_the_bar(pages: TestClient) -> None:
    """A fixed `text-foreground` would be invisible on an inverted header."""
    mark = between(pages.get("/_t/landing").text, '<a href="/" class="', "</a>")

    assert "text-foreground" not in mark


# --- Dark surface -----------------------------------------------------------


def test_a_dark_surface_marks_the_document(pages: TestClient, use_design: UseDesign) -> None:
    use_design(dark=True)

    assert re.search(r'<html lang="es" class="h-full dark">', pages.get("/_t/landing").text)


def test_a_light_surface_adds_no_class(pages: TestClient, use_design: UseDesign) -> None:
    use_design(dark=False)

    assert '<html lang="es" class="h-full">' in pages.get("/_t/landing").text


# --- Motion hooks -----------------------------------------------------------


def test_the_landing_loads_motion_in_the_right_places(
    pages: TestClient, use_design: UseDesign
) -> None:
    use_design(
        motion_level=8,
        motion_head=("js/motion.js",),
        motion_body=("js/vendor/motion.min.js", "js/motion-lib.js"),
    )

    html = pages.get("/_t/landing").text
    head = between(html, "<head>", "</head>")

    assert re.search(r'<script src="/static/js/motion\.js\?v=\d+"></script>', head), (
        "el núcleo va síncrono: la puerta js-motion tiene que estar antes del primer pintado"
    )
    assert head.index("motion.js") < head.index("css/app.css"), "antes del CSS"
    assert " defer" not in re.search(r"<script[^>]*motion\.js[^>]*>", head).group(0)  # type: ignore[union-attr]
    body = html.split("</head>", 1)[1]
    assert body.index("motion.min.js") < body.index("motion-lib.js"), (
        "la librería antes que su adaptador"
    )
    assert re.search(r'<script src="/static/js/motion-lib\.js\?v=\d+" defer></script>', body)


def test_app_pages_never_load_motion(pages: TestClient, use_design: UseDesign) -> None:
    use_design(
        motion_level=9,
        motion_head=("js/motion.js",),
        motion_body=("js/vendor/gsap.min.js", "js/motion-gsap.js"),
    )

    for path in ("/_t/app", "/login", "/register", "/no-existe"):
        assert "motion" not in pages.get(path).text.replace("motion-safe", ""), path


def test_low_levels_load_nothing_even_on_a_landing(
    pages: TestClient, use_design: UseDesign
) -> None:
    use_design(motion_level=3)

    assert "/static/js/motion" not in pages.get("/_t/landing").text


def test_the_text_font_is_preloaded_before_the_stylesheet(
    pages: TestClient, use_design: UseDesign
) -> None:
    use_design(preload_fonts=("/static/fonts/inter-latin-400-normal.woff2",))

    head = between(pages.get("/_t/landing").text, "<head>", "</head>")

    link = (
        '<link rel="preload" href="/static/fonts/inter-latin-400-normal.woff2" '
        'as="font" type="font/woff2" crossorigin>'
    )
    assert link in head
    assert head.index("preload") < head.index("css/app.css")


def test_no_preload_without_a_declared_font(pages: TestClient, use_design: UseDesign) -> None:
    use_design()  # a runtime with no fonts, whatever the project declares

    assert 'rel="preload"' not in pages.get("/_t/landing").text


# --- The runtime ------------------------------------------------------------


def contract(**tables: object) -> DesignContract:
    return DesignContract.model_validate(tables)


def test_runtime_reads_the_slice_templates_need(tmp_path: Path) -> None:
    runtime = runtime_from_contract(
        contract(
            brand={"surface": "dark"}, structure={"header": "terminal-bar"}, motion={"level": 5}
        ),
        tmp_path,
    )

    assert runtime.dark and runtime.html_class == "dark"
    assert runtime.header == "terminal-bar"
    assert runtime.motion_level == 5


def test_runtime_preloads_only_a_font_that_exists(tmp_path: Path) -> None:
    body = {"type": {"body": {"name": "Inter", "weights": [300, 400, 700]}}}
    assert runtime_from_contract(contract(**body), tmp_path).preload_fonts == ()

    (tmp_path / "fonts").mkdir()
    (tmp_path / "fonts" / "inter-latin-400-normal.woff2").write_bytes(make_woff2())

    assert runtime_from_contract(contract(**body), tmp_path).preload_fonts == (
        "/static/fonts/inter-latin-400-normal.woff2",
    )


def test_runtime_preloads_the_lightest_weight_when_there_is_no_regular(tmp_path: Path) -> None:
    (tmp_path / "fonts").mkdir()
    (tmp_path / "fonts" / "inter-latin-500-normal.woff2").write_bytes(make_woff2())

    runtime = runtime_from_contract(
        contract(type={"body": {"name": "Inter", "weights": [500, 700]}}), tmp_path
    )

    assert runtime.preload_fonts == ("/static/fonts/inter-latin-500-normal.woff2",)


def test_runtime_never_preloads_the_display_face(tmp_path: Path) -> None:
    """One preload is a win; three compete with the stylesheet."""
    (tmp_path / "fonts").mkdir()
    (tmp_path / "fonts" / "fraunces-latin-400-normal.woff2").write_bytes(make_woff2())

    runtime = runtime_from_contract(
        contract(type={"display": {"name": "Fraunces", "weights": [400]}}), tmp_path
    )

    assert runtime.preload_fonts == ()


def test_the_proxy_follows_design_toml_in_development(tmp_path: Path) -> None:
    paths = Paths(tmp_path)
    paths.contract.write_text(dump_contract(DesignContract()), encoding="utf-8")
    proxy = DesignProxy(tmp_path, paths.static, watch=True)
    assert proxy.header == "sticky-blur"

    paths.contract.write_text(dump_contract(PRESETS["brutalista"].contract), encoding="utf-8")
    import os

    os.utime(paths.contract, ns=(10**18, 10**18))  # a clearly newer mtime, whatever the fs clock

    assert proxy.header == "industrial-rule"


def test_the_proxy_resolves_once_in_production(tmp_path: Path) -> None:
    paths = Paths(tmp_path)
    paths.contract.write_text(dump_contract(DesignContract()), encoding="utf-8")
    proxy = DesignProxy(tmp_path, paths.static, watch=False)
    assert proxy.header == "sticky-blur"

    paths.contract.write_text(dump_contract(PRESETS["brutalista"].contract), encoding="utf-8")

    assert proxy.header == "sticky-blur"


def test_a_broken_design_toml_never_takes_the_site_down(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    paths = Paths(tmp_path)
    paths.contract.write_text('[brand]\nprimary = "x"', encoding="utf-8")
    proxy = DesignProxy(tmp_path, paths.static, watch=True)

    with caplog.at_level(logging.WARNING, logger="app.design"):
        assert proxy.header == "sticky-blur"

    assert "design.toml ignorado" in caplog.text


def test_a_missing_design_toml_means_the_defaults(tmp_path: Path) -> None:
    proxy = DesignProxy(tmp_path, tmp_path / "static", watch=True)

    assert proxy.header == "sticky-blur" and not proxy.dark and proxy.motion_level == 3


def test_the_proxy_does_not_answer_for_private_names(tmp_path: Path) -> None:
    proxy = DesignProxy(tmp_path, tmp_path, watch=True)

    with pytest.raises(AttributeError):
        proxy._anything  # noqa: B018


# --- /_design ---------------------------------------------------------------


def test_the_design_page_renders_every_section(
    client: TestClient, project_contract: Callable[[DesignContract], None]
) -> None:
    project_contract(contract(brand={"surface": "light"}, motion={"level": 5}))
    response = client.get("/_design")
    html = response.text

    assert response.status_code == 200
    for section in (
        "estilos",
        "tokens",
        "tipografia",
        "botones",
        "formularios",
        "superficies",
        "hero",
        "motion",
        "oscuro",
    ):
        assert f'id="{section}"' in html, section
    assert '<meta name="robots" content="noindex">' in html
    assert "Alternar modo oscuro" in html


def test_the_design_page_shows_every_token_with_its_contrast(
    client: TestClient, project_contract: Callable[[DesignContract], None]
) -> None:
    project_contract(contract(brand={"surface": "light"}))
    html = client.get("/_design").text

    for token in (
        "--background",
        "--card",
        "--primary",
        "--secondary",
        "--muted",
        "--accent",
        "--sidebar",
    ):
        assert f"var({token})" in html or token in html
    assert re.search(r"claro\s+\d+\.\d\s*·\s*oscuro\s+\d+\.\d", html)


def test_the_design_page_says_when_nothing_has_been_chosen(
    client: TestClient, project_contract: Callable[[DesignContract], None]
) -> None:
    """A contract in the defaults must read as unfinished, not look like a design."""
    project_contract(DesignContract())
    assert "design.toml sigue en los valores por defecto" in client.get("/_design").text

    project_contract(PRESETS["editorial"].contract)
    assert "design.toml sigue en los valores por defecto" not in client.get("/_design").text


def test_the_dark_mode_toggle_is_offered_only_to_projects_that_have_a_light_mode(
    client: TestClient, project_contract: Callable[[DesignContract], None]
) -> None:
    project_contract(contract(brand={"surface": "light"}))
    assert "Alternar modo oscuro" in client.get("/_design").text

    project_contract(contract(brand={"surface": "dark"}))
    assert "Alternar modo oscuro" not in client.get("/_design").text


def test_the_design_page_has_no_cookie_banner(client: TestClient) -> None:
    assert "Usamos cookies" not in client.get("/_design").text


def test_every_style_can_be_previewed_without_writing_anything(client: TestClient) -> None:
    for name in PRESETS:
        response = client.get(f"/_design?style={name}")
        html = response.text

        assert response.status_code == 200, name
        assert '<style id="design-preview">' in html
        assert f"Vista previa: estilo {name}" in html
        assert "kiro:brand:start" in html  # the same block the compiler would write


def test_a_preview_can_override_single_brand_keys(client: TestClient) -> None:
    html = client.get("/_design?style=brutalista&surface=cream&primary=%230F766E").text

    label = between(html, "Vista previa: ", ".</strong>")
    assert {part.strip() for part in label.split(",")} == {
        "estilo brutalista",
        "surface=cream",
        "primary=#0F766E",
    }
    assert "--radius: 0rem;" in html, "el radio del estilo se conserva"
    assert "oklch(0.972" in html, "y la superficie pedida se aplica"


@pytest.mark.parametrize(
    "query",
    [
        "primary=verde",
        "primary=%3Cscript%3Ealert(1)%3C/script%3E",
        "radius=1rem%3B%7D%3C/style%3E%3Cscript%3Ealert(1)%3C/script%3E",
        "neutral=%22%3E%3Cimg%20src=x%20onerror=alert(1)%3E",
        "surface=neon",
        "style=barroco",
        "style=%3Cscript%3Ealert(1)%3C/script%3E",
    ],
)
def test_a_bad_preview_is_a_400_and_never_echoes_markup(client: TestClient, query: str) -> None:
    response = client.get(f"/_design?{query}")

    assert response.status_code == 400
    assert "<script>alert" not in response.text
    assert "onerror=alert" not in response.text
    assert '<style id="design-preview">' not in response.text
    assert 'role="alert"' in response.text


def test_previewing_an_unreadable_colour_shows_the_failure_instead_of_hiding_it(
    client: TestClient,
) -> None:
    """#E11D48 is a fine brand colour at 4.49:1; the page must say what the build would."""
    response = client.get("/_design?primary=%23E11D48")

    assert response.status_code == 200
    assert "No cumple WCAG AA" in response.text
    assert "--primary-foreground sobre --primary" in response.text
    assert "se negaría a compilarla" in response.text


def test_a_readable_preview_has_no_contrast_warning(client: TestClient) -> None:
    assert "No cumple WCAG AA" not in client.get("/_design?style=suave-premium").text


def test_the_design_page_does_not_exist_in_production(db_session, mailbox) -> None:  # type: ignore[no-untyped-def]
    settings = get_settings().model_copy(update={"environment": Environment.PRODUCTION})
    app = create_app(settings, enforce_csrf=False)
    override_dependencies(app, db_session, mailbox, settings)

    with TestClient(app) as deployed:
        assert deployed.get("/_design").status_code == 404
        assert deployed.get("/_design?style=brutalista").status_code == 404


def test_the_design_page_can_be_switched_off_in_development(db_session, mailbox) -> None:  # type: ignore[no-untyped-def]
    settings = get_settings().model_copy(update={"design_preview": False})
    app = create_app(settings, enforce_csrf=False)
    override_dependencies(app, db_session, mailbox, settings)

    with TestClient(app) as local:
        assert local.get("/_design").status_code == 404


def test_the_design_page_is_not_in_the_sitemap_or_robots(client: TestClient) -> None:
    assert "_design" not in client.get("/sitemap.xml").text


def test_the_flag_is_documented_in_the_env_template() -> None:
    env = (Path(__file__).resolve().parent.parent / ".env.example").read_text(encoding="utf-8")

    assert "DESIGN_PREVIEW=true" in env


# --- /_design follows the contract -----------------------------------------


@pytest.fixture
def project_contract(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Callable[[DesignContract], None]:
    """Point the design service at a temp project, to render other contracts."""
    paths = Paths(tmp_path)
    monkeypatch.setattr(design_service, "Paths", lambda: paths)

    def write(value: DesignContract) -> None:
        paths.contract.write_text(dump_contract(value), encoding="utf-8")

    return write


def test_the_motion_section_shows_only_what_the_level_provides(
    client: TestClient, project_contract: Callable[[DesignContract], None]
) -> None:
    def section(level: int) -> str:
        project_contract(contract(motion={"level": level}))
        return between(client.get("/_design").text, 'id="motion"', 'id="oscuro"')

    low = section(3)
    assert "Sube" in low and "data-motion=" not in low

    core = section(5)
    for value in ("split-reveal", "reveal", "stagger", "count", "marquee"):
        assert f'data-motion="{value}"' in core
    assert 'data-motion="parallax"' not in core

    lib = section(8)
    assert 'data-motion="parallax"' in lib and 'data-motion-ease="spring"' in lib
    assert 'data-motion="scrub"' not in lib

    gsap = section(9)
    assert 'data-motion="scrub"' in gsap


def test_the_design_page_follows_the_contract_it_reads(
    client: TestClient, project_contract: Callable[[DesignContract], None]
) -> None:
    project_contract(PRESETS["suave-premium"].contract)

    html = client.get("/_design").text

    assert "#3F6B5A" in html and "Fraunces" in html and "floating-pill" in html
    assert "valores por defecto" not in html


def test_a_broken_contract_is_reported_on_the_page(
    client: TestClient, project_contract: Callable[[DesignContract], None], tmp_path: Path
) -> None:
    (tmp_path / "design.toml").write_text('[brand]\nprimary = "x"', encoding="utf-8")

    response = client.get("/_design")

    assert response.status_code == 200
    assert "brand.primary" in response.text
