"""What the templates need to know about the design, at request time.

Colours and fonts are compiled into CSS and cost nothing at runtime. A few
decisions are about *markup*, though, and only a template can act on them:

    dark          the surface is dark, so `<html>` must carry the `dark` class
    header        which header partial `partials/header.html` includes
    motion        which scripts the landing layout loads
    preload       the body font, so text does not flash in a fallback

They are read from `design.toml` and exposed to Jinja as the `design` global
(see `app/templating.py`). A missing or broken file means the defaults and a
log line, never a crashed page: the identity should not take the site down.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.design_engine.contract import (
    CONTRACT_FILE,
    DesignContract,
    DesignError,
    load_contract,
)
from app.design_engine.fonts import FONTS_URL_PREFIX, font_filename
from app.design_engine.motion import scripts_for

logger = logging.getLogger("app.design")


@dataclass(frozen=True)
class DesignRuntime:
    """The slice of the contract that templates read."""

    dark: bool = False
    header: str = "sticky-blur"
    motion_level: int = 3
    preload_fonts: tuple[str, ...] = ()
    motion_head: tuple[str, ...] = ()
    motion_body: tuple[str, ...] = ()

    @property
    def html_class(self) -> str:
        return "dark" if self.dark else ""


def runtime_from_contract(contract: DesignContract, static_dir: Path) -> DesignRuntime:
    """Resolve `contract` against the files that actually exist under `static_dir`."""
    preload: list[str] = []
    body = contract.typography.body
    if body is not None:
        # The regular weight carries nearly all running text; preloading more
        # than one file costs more than the swap it avoids.
        weight = 400 if 400 in body.weights else body.weights[0]
        filename = font_filename(body.slug, weight)
        if (static_dir / "fonts" / filename).is_file():
            preload.append(f"{FONTS_URL_PREFIX}/{filename}")

    head, rest = scripts_for(contract.motion.level, static_dir)
    return DesignRuntime(
        dark=contract.brand.surface == "dark",
        header=contract.structure.header,
        motion_level=contract.motion.level,
        preload_fonts=tuple(preload),
        motion_head=head,
        motion_body=rest,
    )


class DesignProxy:
    """The `design` template global: a `DesignRuntime` that follows `design.toml`.

    In development the contract is re-read when the file, or the font and
    vendor folders, change, so `make design build` shows up on the next request
    without restarting the server (uvicorn's reload only watches `.py` files).
    In production it is resolved once.
    """

    def __init__(self, root: Path, static_dir: Path, *, watch: bool) -> None:
        self._contract_path = root / CONTRACT_FILE
        self._static_dir = static_dir
        self._watch = watch
        self._stamp: tuple[int, ...] | None = None
        self._runtime = DesignRuntime()

    def _fingerprint(self) -> tuple[int, ...]:
        paths = (
            self._contract_path,
            self._static_dir / "fonts",
            self._static_dir / "js",
            self._static_dir / "js" / "vendor",
        )
        stamp: list[int] = []
        for path in paths:
            try:
                stamp.append(path.stat().st_mtime_ns)
            except OSError:
                stamp.append(0)
        return tuple(stamp)

    def current(self) -> DesignRuntime:
        if self._stamp is not None and not self._watch:
            return self._runtime
        stamp = self._fingerprint()
        if stamp != self._stamp:
            self._stamp = stamp
            self._runtime = self._load()
        return self._runtime

    def _load(self) -> DesignRuntime:
        try:
            contract = load_contract(self._contract_path)
        except DesignError as exc:
            logger.warning("design.toml ignorado, usando los valores por defecto: %s", exc)
            contract = DesignContract()
        return runtime_from_contract(contract, self._static_dir)

    def __getattr__(self, name: str) -> Any:
        # Only reached for names that are not attributes of the proxy itself,
        # which is exactly the set of fields Jinja asks `design` for.
        if name.startswith("_"):
            raise AttributeError(name)
        return getattr(self.current(), name)
