"""The UX floor: what every page must satisfy, whatever its design.

These are the first categories of the uupm guide that markup can prove:
accessibility (a language, a title, one `h1`, a name for everything you can
press or type in, an `alt` on every image) and the rest of what keeps a page
usable on a phone (zoom allowed, no positive `tabindex`). A style, a brief or
`DESIGN.md` can change how a page looks; none of them can make it fail these.

Every GET route without a parameter is rendered, anonymous and logged in, so a
page a project adds is covered the day it is added. A route with a parameter
goes in `PARAMETERISED` with an example path. Nothing here is specific to the
framework's own pages: it ships with every project and runs in `make check`.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Iterator
from html.parser import HTMLParser

import pytest
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from app.main import create_app

#: Routes with a path parameter, each with a path that renders. A project adds its own.
PARAMETERISED = {
    "/reset-password/{token}": "/reset-password/un-enlace-que-no-existe",
}

#: Not pages for a visitor: machine output, the design showcase (it shows raw values on
#: purpose and has its own tests) and HTMX fragments, which are a piece of a page and
#: never a document. A project lists its own fragment routes here.
NOT_PAGES = {
    "/health",
    "/robots.txt",
    "/sitemap.xml",
    "/_design",
    "/docs",
    "/docs/oauth2-redirect",
    "/openapi.json",
    "/demo/ping",
}

_NAMELESS_INPUTS = {"hidden", "submit", "button", "image", "reset"}
_VOID = {"input", "img", "br", "hr", "meta", "link", "source", "wbr", "area", "base", "col"}


class Audit(HTMLParser):
    """Collects what the floor looks at, in one pass."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.problems: list[str] = []
        self.lang = ""
        self.title = ""
        self.h1 = 0
        self.main = 0
        self.ids: list[str] = []
        self.label_for: set[str] = set()
        self.fields: list[tuple[str, dict[str, str | None], bool]] = []
        self._open: list[dict[str, object]] = []
        self._in_title = False
        self._label_depth = 0
        self.skip_link_target = ""

    # -- parsing ---------------------------------------------------------------

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        a = dict(attrs)
        if a.get("id"):
            self.ids.append(str(a["id"]))
        if a.get("tabindex") and re.fullmatch(r"[1-9]\d*", str(a["tabindex"]).strip()):
            self.problems.append(f"tabindex positivo en <{tag}> ({a['tabindex']})")

        if tag == "html":
            self.lang = (a.get("lang") or "").strip()
        elif tag == "title":
            self._in_title = True
        elif tag == "h1":
            self.h1 += 1
        elif tag == "main":
            self.main += 1
        elif tag == "meta" and a.get("name") == "viewport":
            content = (a.get("content") or "").replace(" ", "").lower()
            if "user-scalable=no" in content or re.search(r"maximum-scale=1(\.0)?(,|$)", content):
                self.problems.append("el viewport impide hacer zoom")
        elif tag == "label":
            self._label_depth += 1
            if a.get("for"):
                self.label_for.add(str(a["for"]))
        elif tag == "img":
            if "alt" not in a:
                self.problems.append(f"<img src={a.get('src')!r}> sin alt")
            if not (a.get("width") and a.get("height")):
                self.problems.append(f"<img src={a.get('src')!r}> sin width y height")
        elif tag == "a" and a.get("href", "").startswith("#") and len(a.get("href") or "") > 1:
            self.skip_link_target = self.skip_link_target or str(a["href"])[1:]

        if tag in ("input", "select", "textarea"):
            kind = (a.get("type") or "text").lower() if tag == "input" else tag
            if kind not in _NAMELESS_INPUTS:
                self.fields.append((tag, a, self._label_depth > 0))
        if tag in ("button", "a", "label"):
            self._open.append({"tag": tag, "attrs": a, "text": "", "named": self._named(a)})
        elif self._open and (
            (tag == "img" and (a.get("alt") or "").strip())
            or (tag == "svg" and (a.get("aria-label") or a.get("aria-labelledby")))
        ):
            self._open[-1]["named"] = True
        if tag in _VOID:
            return

    @staticmethod
    def _named(a: dict[str, str | None]) -> bool:
        return bool(
            (a.get("aria-label") or a.get("aria-labelledby") or a.get("title") or "").strip()
        )

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self._in_title = False
        elif tag == "label":
            self._label_depth = max(0, self._label_depth - 1)
        if tag in ("button", "a") and self._open and self._open[-1]["tag"] == tag:
            item = self._open.pop()
            attrs = item["attrs"]
            assert isinstance(attrs, dict)
            is_link = tag == "a" and attrs.get("href") is None
            if is_link or item["named"] or str(item["text"]).strip():
                return
            self.problems.append(f"<{tag}> sin nombre accesible ({attrs.get('href') or attrs})")
        elif tag == "label" and self._open and self._open[-1]["tag"] == "label":
            self._open.pop()

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self.title += data
        if self._open:
            self._open[-1]["text"] = str(self._open[-1]["text"]) + data

    # -- the verdict -----------------------------------------------------------------

    def verdict(self) -> list[str]:
        problems = list(self.problems)
        if not self.lang:
            problems.append("<html> sin lang")
        if not self.title.strip():
            problems.append("<title> vacío")
        if self.h1 != 1:
            problems.append(f"debe haber exactamente un <h1> y hay {self.h1}")
        if self.main != 1:
            problems.append(f"debe haber exactamente un <main> y hay {self.main}")
        duplicated = sorted({i for i in self.ids if self.ids.count(i) > 1})
        if duplicated:
            problems.append(f"ids repetidos: {', '.join(duplicated)}")
        for tag, a, wrapped in self.fields:
            named = (
                wrapped
                or (a.get("id") in self.label_for)
                or bool((a.get("aria-label") or a.get("aria-labelledby") or "").strip())
            )
            if not named:
                problems.append(f"<{tag} name={a.get('name')!r}> sin label")
        if self.skip_link_target and self.skip_link_target not in self.ids:
            problems.append(f"el enlace #{self.skip_link_target} no tiene destino")
        return problems


def audit(html: str) -> list[str]:
    parser = Audit()
    parser.feed(html)
    parser.close()
    return parser.verdict()


# --- The auditor itself: it must catch what it claims to ----------------------------------

GOOD = """<!doctype html><html lang="es"><head><title>T</title>
<meta name="viewport" content="width=device-width, initial-scale=1"></head>
<body><a href="#main">Saltar</a><main id="main"><h1>H</h1>
<label for="a">A</label><input id="a" name="a">
<label>B <input name="b"></label><input name="c" aria-label="C"><input type="hidden" name="d">
<img src="/x.png" alt="" width="1" height="1"><button>Ok</button>
<button aria-label="Cerrar"><svg aria-hidden="true"></svg></button></main></body></html>"""


def test_a_correct_page_has_no_problems() -> None:
    assert audit(GOOD) == []


@pytest.mark.parametrize(
    ("needle", "page"),
    [
        ("sin lang", GOOD.replace('lang="es"', "")),
        ("<title> vacío", GOOD.replace("<title>T</title>", "<title></title>")),
        ("exactamente un <h1> y hay 0", GOOD.replace("<h1>H</h1>", "")),
        ("exactamente un <h1> y hay 2", GOOD.replace("<h1>H</h1>", "<h1>H</h1><h1>I</h1>")),
        ("exactamente un <main>", GOOD.replace("<main", "<div").replace("</main>", "</div>")),
        ("ids repetidos", GOOD.replace('id="a"', 'id="main"').replace('for="a"', 'for="main"')),
        ("sin label", GOOD.replace('<label for="a">A</label>', "")),
        ("sin alt", GOOD.replace('alt="" ', "")),
        ("sin width y height", GOOD.replace(' width="1" height="1"', "")),
        ("sin nombre accesible", GOOD.replace("<button>Ok</button>", "<button></button>")),
        ("tabindex positivo", GOOD.replace("<h1>", '<h1 tabindex="3">')),
        ("impide hacer zoom", GOOD.replace("initial-scale=1", "initial-scale=1, user-scalable=no")),
        ("no tiene destino", GOOD.replace('id="main"', 'id="otro"')),
    ],
)
def test_the_auditor_catches_each_failure(needle: str, page: str) -> None:
    assert any(needle in problem for problem in audit(page)), audit(page)


def test_an_icon_only_link_needs_a_name() -> None:
    page = GOOD.replace("<button>Ok</button>", '<a href="/x"><svg aria-hidden="true"></svg></a>')

    assert any("sin nombre accesible" in p for p in audit(page))
    named = page.replace('<a href="/x">', '<a href="/x" aria-label="Ir">')
    assert audit(named) == []


# --- The pages ---------------------------------------------------------------------------------


def _all_routes(routes: Iterable[object], prefix: str = "") -> Iterator[tuple[str, set[str]]]:
    """`(path, methods)` for every route, through the routers FastAPI wraps on include."""
    for route in routes:
        inner = getattr(route, "original_router", None)
        if inner is not None:
            context = getattr(route, "include_context", None)
            yield from _all_routes(inner.routes, prefix + getattr(context, "prefix", ""))
        elif isinstance(route, APIRoute):
            yield prefix + route.path, set(route.methods)


def _get_paths() -> list[str]:
    return sorted({path for path, methods in _all_routes(create_app().routes) if "GET" in methods})


def _routes() -> list[str]:
    paths = []
    for path in _get_paths():
        if path in NOT_PAGES or path.startswith("/static"):
            continue
        paths.append(PARAMETERISED.get(path, path) if "{" in path else path)
    return sorted(set(paths))


def _check(client: TestClient, path: str) -> None:
    response = client.get(path)
    if response.status_code in (301, 302, 303, 307, 308):
        return  # a private page seen anonymously: it redirects to the login
    assert response.status_code in (200, 400, 403, 404), (path, response.status_code)
    assert response.headers["content-type"].startswith("text/html"), path
    assert audit(response.text) == [], f"{path}: {audit(response.text)}"


def test_the_floor_finds_the_pages_of_the_project() -> None:
    """A parametrised test over an empty list passes by skipping: do not let it."""
    pages = _routes()

    assert {"/", "/login", "/register", "/forgot-password", "/notes"} <= set(pages)


def test_every_route_with_a_parameter_has_an_example() -> None:
    parameterised = {
        p for p in _get_paths() if "{" in p and p not in NOT_PAGES and p not in PARAMETERISED
    }

    assert not parameterised, f"añade un ejemplo en PARAMETERISED para: {sorted(parameterised)}"


@pytest.mark.parametrize("path", _routes())
def test_every_page_meets_the_floor_anonymous(client: TestClient, path: str) -> None:
    _check(client, path)


@pytest.mark.parametrize("path", _routes())
def test_every_page_meets_the_floor_logged_in(logged_in_client: TestClient, path: str) -> None:
    _check(logged_in_client, path)


def test_the_error_pages_meet_the_floor(client: TestClient) -> None:
    for path in ("/esta-pagina-no-existe",):
        _check(client, path)
