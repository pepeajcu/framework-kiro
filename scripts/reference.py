"""Take the visual language of a reference, and turn it into a proposal.

    make design-reference url=https://example.com [name=x]        # read its CSS
    make design-reference skillui=https://example.com [mode=ultra] # through skillui
    make design-reference skillui_dir=./salida-de-skillui
    make design-reference md=./style.md                            # a Refero "Copy .md"

Whichever way it comes in, the result is a `DesignBrief` saved in `.design/briefs/` and
a **proposal** in `.design/proposals/`, which a person reads and applies with
`make design-apply` (references/constitution.md, ADR-0018 and ADR-0021).

**What is taken, and what never is.** The language: colours (one accent survives), the
names of the font families (mapped to Fontsource, never copied), a corner radius, how
much it moves, what to avoid. Not its logo, images, text, fonts or component code, and
nothing is downloaded but the page and its stylesheets, as text. The URL goes into
`DESIGN.md` under *Procedencia*, and the visual signature stays the project's own.

skillui is an optional Node tool installed by the person (`npm i -g skillui`); it is not a
dependency (ADR-0005) and is always run with `--out` pointing at `.design/reference/`,
because without it skillui writes `DESIGN.md` and `CLAUDE.md` into the current directory.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import shutil
import subprocess
import sys
from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from urllib.parse import urljoin, urlparse

import httpx2

from app.branding import BrandError, parse_hex, rgb_to_oklch
from app.design_engine.brief import BriefColour, BriefFont, DesignBrief, FontRole
from app.design_engine.contract import DesignError
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
from scripts import design as design_cli
from scripts.fetch import fetch_bytes

PAGE_LIMIT = 1_500_000
SHEET_LIMIT = 1_500_000
MAX_SHEETS = 8
SKILLUI_TIMEOUT = 300.0

_STYLESHEET = re.compile(r"<link\b[^>]*>", re.IGNORECASE)
_HREF = re.compile(r"""href\s*=\s*["']([^"']+)["']""", re.IGNORECASE)
_STYLE_BLOCK = re.compile(r"<style\b[^>]*>(.*?)</style>", re.IGNORECASE | re.DOTALL)
_TITLE = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)
_RULE = re.compile(r"([^{}@][^{}]*)\{([^{}]*)\}")
_COMMENT = re.compile(r"/\*.*?\*/", re.DOTALL)
_DECL = re.compile(r"([a-z-]+)\s*:\s*([^;]+)", re.IGNORECASE)
_BRAND_SELECTOR = re.compile(r"btn|button|cta|primary|accent|\blink|(^|[\s,>])a(?![\w-])", re.I)
_DISPLAY_SELECTOR = re.compile(r"(^|[\s,>])h[1-3](?![\w-])|display|hero|headline|title", re.I)
_MONO_SELECTOR = re.compile(r"\bcode\b|\bpre\b|\bkbd\b|\bsamp\b|mono", re.I)
_MOTION_LIBRARIES = re.compile(
    r"gsap|scrolltrigger|lottie|framer-motion|three\.js|locomotive", re.I
)


def _check_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise DesignError(f"'{url}' no es una URL http(s)")
    return url


# --- Reading a site ------------


def _sheets(html: str, base: str) -> list[str]:
    urls: list[str] = []
    for tag in _STYLESHEET.findall(html):
        if re.search(r"""rel\s*=\s*["']?[^"'>]*stylesheet""", tag, re.IGNORECASE):
            match = _HREF.search(tag)
            if match and not match.group(1).startswith("data:"):
                urls.append(urljoin(base, match.group(1)))
    return urls[:MAX_SHEETS]


def analyse_css(css: str, html: str = "") -> DesignBrief:
    """The language of a stylesheet (and the page that loads it), as a brief."""
    css = _COMMENT.sub("", css)
    colours: Counter[str] = Counter()
    brand: Counter[str] = Counter()
    roles: dict[str, str] = {}
    fonts: dict[FontRole, Counter[str]] = {
        "display": Counter(),
        "body": Counter(),
        "mono": Counter(),
    }
    generics: dict[str, str] = {}
    radii: list[str] = []
    transitions = animations = 0
    body_background = ""

    for selector, block in _RULE.findall(css):
        selector = " ".join(selector.split())
        for prop, value in _DECL.findall(block):
            prop = prop.lower()
            if prop.startswith("--"):
                for hex_value in find_colours(value):
                    colours[hex_value] += 1
                    roles.setdefault(hex_value, role_of(prop))
                continue
            if prop in (
                "color",
                "background",
                "background-color",
                "border-color",
                "fill",
                "stroke",
            ):
                for hex_value in find_colours(value):
                    colours[hex_value] += 1
                    if _BRAND_SELECTOR.search(selector) and prop != "color":
                        brand[hex_value] += 1
                    if re.fullmatch(r"(html|body|:root)(\s*,\s*(html|body))*", selector):
                        if prop in ("background", "background-color"):
                            body_background = hex_value
                            roles[hex_value] = "background"
                        elif prop == "color":
                            roles.setdefault(hex_value, "text")
            elif prop == "font-family":
                family = clean_family(value)
                if family:
                    role: FontRole = (
                        "mono"
                        if _MONO_SELECTOR.search(selector)
                        else "display"
                        if _DISPLAY_SELECTOR.search(selector)
                        else "body"
                    )
                    fonts[role][family] += 1
                    generics.setdefault(family, value)
            elif prop == "border-radius":
                radii.append(value)
            elif prop.startswith("transition"):
                transitions += 1
            elif prop.startswith("animation"):
                animations += 1
    keyframes = len(re.findall(r"@keyframes", css))

    # One accent: the colour the buttons and links are filled with, if any; else the most
    # used chromatic one. Greys are left to `propose`, which ignores low chroma.
    ranked = [h for h, _ in brand.most_common()] + [h for h, _ in colours.most_common()]
    accent = next((h for h in ranked if _chromatic(h)), None)
    most = max(colours.values(), default=1)
    palette = [
        BriefColour(
            hex=h,
            role="primary" if h == accent else roles.get(h, "other"),  # type: ignore[arg-type]
            weight=round(min(1.0, (n + brand[h] * 4) / (most + 4)), 3),
        )
        for h, n in colours.most_common(24)
    ]

    brief_fonts: list[BriefFont] = []
    for font_role in ("display", "body", "mono"):
        if fonts[font_role]:
            family = fonts[font_role].most_common(1)[0][0]
            category = (
                "mono" if font_role == "mono" else category_of(family, generic_of(generics[family]))
            )
            default = {"display": (600, 700), "body": (400, 600), "mono": (400,)}[font_role]
            brief_fonts.append(
                BriefFont(name=family, role=font_role, category=category, weights=default)
            )
    if (
        len(brief_fonts) >= 2
        and brief_fonts[0].role == "display"
        and brief_fonts[0].name == brief_fonts[1].name
    ):
        brief_fonts = brief_fonts[1:]

    surface = None
    if body_background:
        try:
            surface = "dark" if rgb_to_oklch(parse_hex(body_background))[0] < 0.35 else None
        except BrandError:
            surface = None

    if _MOTION_LIBRARIES.search(html + css):
        motion = 8
    elif keyframes >= 4 or animations >= 6:
        motion = 6
    elif transitions or keyframes:
        motion = 4
    else:
        motion = 2

    return DesignBrief(
        source="reference",
        provenance="referencia",
        colours=tuple(palette),
        fonts=tuple(brief_fonts),
        radius=radius_from(radii),
        surface=surface,  # type: ignore[arg-type]
        motion=motion,
    )


def _chromatic(hex_value: str) -> bool:
    try:
        return rgb_to_oklch(parse_hex(hex_value))[1] >= 0.04
    except BrandError:
        return False


def capture(
    url: str, *, client: httpx2.Client | None = None, today: dt.date | None = None
) -> DesignBrief:
    """Read a site's page and stylesheets (as text) and describe its visual language."""
    url = _check_url(url)
    today = today or dt.datetime.now(tz=dt.UTC).date()
    html = fetch_bytes(url, limit=PAGE_LIMIT, label=url, client=client).decode("utf-8", "replace")
    css = "\n".join(_STYLE_BLOCK.findall(html))
    for sheet in _sheets(html, url):
        try:
            css += "\n" + fetch_bytes(sheet, limit=SHEET_LIMIT, label=sheet, client=client).decode(
                "utf-8", "replace"
            )
        except DesignError as exc:
            print(f"aviso: {exc}", file=sys.stderr)
    if not css.strip():
        raise DesignError(f"{url} no trae CSS que leer (¿se pinta con JavaScript? prueba skillui)")

    brief = analyse_css(css, html)
    title = _TITLE.search(html)
    name = " ".join(title.group(1).split())[:80] if title else urlparse(url).netloc
    return brief.model_copy(
        update={
            "title": name or urlparse(url).netloc,
            "provenance": f"{url} (capturado el {today.isoformat()})",
        }
    )


# --- skillui and pasted files ------------


def _json(path: Path) -> Mapping[str, object] | None:
    if not path.is_file() or path.stat().st_size > 2_000_000:
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except ValueError:
        return None
    return data if isinstance(data, dict) else None


def from_skillui_dir(folder: Path, *, provenance: str | None = None) -> DesignBrief:
    """Read what skillui wrote in `folder`: its token files and `DESIGN.md`."""
    if not folder.is_dir():
        raise DesignError(f"no existe la carpeta de skillui: {folder}")
    design_md = folder / "DESIGN.md"
    text = design_md.read_text(encoding="utf-8") if design_md.is_file() else None
    try:
        return brief_from_skillui(
            colors=_json(folder / "tokens" / "colors.json"),
            typography=_json(folder / "tokens" / "typography.json"),
            spacing=_json(folder / "tokens" / "spacing.json"),
            design_md=text,
            provenance=provenance or f"skillui: {folder.name}",
        )
    except BrandError as exc:
        raise DesignError(str(exc)) from exc


def run_skillui(
    paths: Paths,
    url: str,
    name: str,
    *,
    ultra: bool = False,
    which: Callable[[str], str | None] = shutil.which,
    run: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> Path:
    """Run skillui into `.design/reference/<name>/` and return that folder.

    Always with `--out` (otherwise it writes `DESIGN.md` and `CLAUDE.md` into the
    current directory, over the project's own) and `--no-skill --format design-md` (we
    want the tokens, not a second skill).
    """
    url = _check_url(url)
    executable = which("skillui")
    if executable is None:
        raise DesignError(
            "skillui no está instalado (es opcional: `npm install -g skillui`, Node 18+). "
            "Sin él, `make design-reference url=...` lee el CSS de la web directamente"
        )
    out = paths.work / "reference" / name
    out.mkdir(parents=True, exist_ok=True)
    command = [executable, "--url", url, "--out", str(out), "--name", name]
    command += ["--no-skill", "--format", "design-md"]
    if ultra:
        command += ["--mode", "ultra"]
    try:
        result = run(
            command, capture_output=True, text=True, timeout=SKILLUI_TIMEOUT, check=False, cwd=out
        )
    except subprocess.TimeoutExpired as exc:
        raise DesignError(f"skillui tardó más de {SKILLUI_TIMEOUT:g} s") from exc
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip().splitlines()[-1:] or ["sin detalle"]
        raise DesignError(f"skillui falló: {detail[0]}")
    return out


# --- Command line ------------


def _save_and_propose(
    paths: Paths, brief: DesignBrief, name: str | None, base: Path | None
) -> tuple[str, design_cli.Proposal]:
    slug = design_cli._slug(name or brief.title)
    (paths.work / "briefs").mkdir(parents=True, exist_ok=True)
    target = paths.work / "briefs" / f"{slug}.json"
    design_cli.write_atomically(target, brief.model_dump_json(indent=2) + "\n")
    return design_cli.make_proposal(paths, source=target, base=base, name=slug)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--url", help="leer el CSS de esta web")
    group.add_argument("--skillui", metavar="URL", help="pasar por skillui (opcional)")
    group.add_argument("--skillui-dir", type=Path, help="la carpeta que escribió skillui")
    group.add_argument("--md", type=Path, help="un DESIGN.md (Refero, skillui, Stitch)")
    parser.add_argument("--name", help="nombre de la propuesta")
    parser.add_argument("--base", type=Path, help="brief de base (p. ej. el de uupm)")
    parser.add_argument("--mode", choices=("default", "ultra"), default="default")
    args = parser.parse_args(argv)

    paths = Paths()
    try:
        if args.url:
            brief = capture(args.url)
        elif args.skillui:
            name = design_cli._slug(args.name or urlparse(args.skillui).netloc)
            folder = run_skillui(paths, args.skillui, name, ultra=args.mode == "ultra")
            brief = from_skillui_dir(folder, provenance=f"{args.skillui} (vía skillui)")
        elif args.skillui_dir:
            brief = from_skillui_dir(args.skillui_dir)
        else:
            try:
                text = args.md.read_text(encoding="utf-8")
            except OSError as exc:
                raise DesignError(f"no se puede leer {args.md}: {exc.strerror}") from exc
            try:
                brief = brief_from_markdown(text, source="reference", provenance=f"{args.md.name}")
            except BrandError as exc:
                raise DesignError(str(exc)) from exc
        slug, proposal = _save_and_propose(paths, brief, args.name, args.base)
    except BrandError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(f"referencia '{brief.title}' → propuesta '{slug}' en .design/proposals/")
    for decision in proposal.decisions:
        print(f"  {decision.field}: {decision.before} → {decision.after} ({decision.reason})")
    for note in proposal.notes:
        print(f"  nota: {note}")
    for item in proposal.unresolved:
        print(f"  sin resolver: {item}", file=sys.stderr)
    print(f"revísala y aplícala con `make design-apply proposal={slug}`")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
