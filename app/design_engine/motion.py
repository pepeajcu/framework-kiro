"""Motion levels: which scripts each `motion.level` loads, and what they understand.

The AI never writes JavaScript per page. It writes attributes:

    <h1 data-motion="split-reveal">…</h1>
    <ul data-motion="stagger" data-motion-delay="0.08">…</ul>

and the level in `design.toml` decides how much machinery stands behind them:

    1-3   CSS transitions only. Nothing is loaded.
    4-6   `motion.js`, our own ~3 KB (IntersectionObserver, no dependencies).
    7-8   + Motion (motion.dev), vendored, for scroll-linked and spring effects.
    9-10  + GSAP and ScrollTrigger, vendored, for pinning and scrubbing.

Each higher level understands everything the lower ones do. A `data-motion`
value used above the project's level is ignored by the browser (the content
simply shows, static), and `make design-check` reports it.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

Engine = Literal["css", "core", "motion", "gsap"]

CORE_SCRIPT = "js/motion.js"
MOTION_ADAPTER = "js/motion-lib.js"
GSAP_ADAPTER = "js/motion-gsap.js"
VENDOR_MOTION = "js/vendor/motion.min.js"
VENDOR_GSAP = "js/vendor/gsap.min.js"
VENDOR_SCROLLTRIGGER = "js/vendor/ScrollTrigger.min.js"

# The lowest level at which each `data-motion` value does anything.
# `data-motion-ease="spring"` (spring physics on a reveal) also needs level 7.
VOCABULARY: dict[str, int] = {
    "reveal": 4,
    "stagger": 4,
    "split-reveal": 4,
    "count": 4,
    "marquee": 4,
    "parallax": 7,
    "progress": 7,
    "pin": 9,
    "scrub": 9,
    "horizontal": 9,
}


def engine_for(level: int) -> Engine:
    if level >= 9:
        return "gsap"
    if level >= 7:
        return "motion"
    if level >= 4:
        return "core"
    return "css"


def vendored_files(level: int) -> tuple[str, ...]:
    """Third-party files (under `app/static/`) that `level` needs. Ours are not listed."""
    engine = engine_for(level)
    if engine == "motion":
        return (VENDOR_MOTION,)
    if engine == "gsap":
        return (VENDOR_GSAP, VENDOR_SCROLLTRIGGER)
    return ()


def own_files(level: int) -> tuple[str, ...]:
    """The scripts that ship with the framework for `level`."""
    engine = engine_for(level)
    if engine == "css":
        return ()
    files = [CORE_SCRIPT]
    if engine == "motion":
        files.append(MOTION_ADAPTER)
    elif engine == "gsap":
        files.append(GSAP_ADAPTER)
    return tuple(files)


def scripts_for(level: int, static_dir: Path) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """`(head, body)` script paths, relative to `app/static/`, that exist on disk.

    `head` is the core, loaded synchronously: it must set the `js-motion` gate
    before the first paint, or the page would flash visible, hide, then reveal.
    `body` is everything else, `defer`red in order (a library before its adapter).

    A missing file is skipped rather than raising: a page with no animation is
    still a correct page. `make design-check` is what reports the gap.
    """
    engine = engine_for(level)
    if engine == "css":
        return (), ()

    def present(paths: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(p for p in paths if (static_dir / p).is_file())

    head = present((CORE_SCRIPT,))
    libs: tuple[str, ...] = ()
    if engine == "motion":
        libs = (VENDOR_MOTION, MOTION_ADAPTER)
    elif engine == "gsap":
        libs = (VENDOR_GSAP, VENDOR_SCROLLTRIGGER, GSAP_ADAPTER)
    # An adapter without its library cannot run: load all of the group or none.
    body = present(libs) if len(present(libs)) == len(libs) else ()
    return head, body


def missing_files(level: int, static_dir: Path) -> tuple[str, ...]:
    """Everything `level` needs that is not on disk yet."""
    needed = (*own_files(level), *vendored_files(level))
    return tuple(p for p in needed if not (static_dir / p).is_file())
