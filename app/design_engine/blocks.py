"""Delimited, idempotent blocks inside `input.css`.

The compiler never edits `input.css` freehand: each thing it owns lives between
a pair of markers, so running it twice replaces instead of duplicating and
anything you write *outside* the markers is left alone.

    /* kiro:fonts:start — generado por `make design build`; no editar a mano */
    ...
    /* kiro:fonts:end */
"""

from __future__ import annotations

import re

from app.design_engine.contract import DesignError

# New blocks go right after Basecoat's import and the `@source` lines, so they
# land after the theme and win by order.
SOURCE_ANCHOR = '@source "../../../app/**/*.py";'

_THEME_IMPORT = re.compile(r'@import\s+"\./vendor/basecoat/basecoat-[a-z]+\.css";')
_NOTE = "generado por `make design build`; no editar a mano"


def _start(name: str) -> str:
    return f"/* kiro:{name}:start — {_NOTE} */"


def _end(name: str) -> str:
    return f"/* kiro:{name}:end */"


def _pattern(name: str) -> re.Pattern[str]:
    return re.compile(
        re.escape(f"/* kiro:{name}:start") + r".*?" + re.escape(_end(name)),
        re.DOTALL,
    )


def render_block(name: str, body: str) -> str:
    """`body` wrapped in the markers of block `name`."""
    return f"{_start(name)}\n{body.strip()}\n{_end(name)}"


def find_block(css: str, name: str) -> str | None:
    match = _pattern(name).search(css)
    return match.group(0) if match else None


def apply_block(css: str, name: str, block: str) -> str:
    """Insert or replace block `name`. Idempotent: the second call changes nothing."""
    pattern = _pattern(name)
    if pattern.search(css):
        return pattern.sub(lambda _: block, css, count=1)
    if SOURCE_ANCHOR not in css:
        raise DesignError(
            f"no encuentro dónde insertar el bloque '{name}' en input.css "
            f"(falta la línea `{SOURCE_ANCHOR}`; ¿se reescribió el archivo?)"
        )
    return css.replace(SOURCE_ANCHOR, f"{SOURCE_ANCHOR}\n\n{block}", 1)


def remove_block(css: str, name: str) -> str:
    """Delete block `name` and the blank line it leaves behind, if it exists."""
    pattern = re.compile(r"\n*" + _pattern(name).pattern, re.DOTALL)
    return pattern.sub("", css, count=1)


def apply_theme_block(css: str, theme: str) -> str:
    """Point `input.css` at Basecoat theme `theme`.

    The `@import` is wrapped in markers the first time. A file that still has
    the bare import from the framework's original `input.css` is upgraded in
    place, so projects created before the engine existed work unchanged.
    """
    block = render_block("theme", f'@import "./vendor/basecoat/basecoat-{theme}.css";')
    pattern = _pattern("theme")
    if pattern.search(css):
        return pattern.sub(lambda _: block, css, count=1)
    if _THEME_IMPORT.search(css):
        return _THEME_IMPORT.sub(lambda _: block, css, count=1)
    raise DesignError(
        "no encuentro el `@import` del tema de Basecoat en input.css (¿se reescribió el archivo?)"
    )
