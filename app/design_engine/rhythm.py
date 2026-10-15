"""Vertical rhythm, compiled from `[structure] density`.

`VISUAL_DENSITY` was a number in `DESIGN.md` that nothing used: a project at 2 (a gallery)
and one at 9 (a cockpit) got the same paddings, because every template wrote its own
`py-16`. The dial is now a contract value, and the three measures that make a page feel
airy or packed come from it:

    --kiro-section-y   the vertical padding of a page section   -> `section-y`
    --kiro-gap         the gap between items of a grid or stack -> `gap-rhythm`
    --kiro-row-h       the minimum height of a list or table row -> `min-h-row`

A template says `section-y` instead of `py-16 sm:py-24` and follows the project's density
without knowing it. Only the *rhythm* is compiled: the shape of a page (its archetype) stays
a recipe, because turning archetypes into macros would make the catalogue a cage (ADR-0014).

Phones get a tighter section padding, and on a coarse pointer a row never goes below 44 px
(the floor of `kiro:a11y`).
"""

from __future__ import annotations

from app.design_engine.blocks import render_block

DEFAULT_DENSITY = 5
TOUCH_ROW_REM = 2.75
PHONE_SECTION_FACTOR = 0.65

#: Index 0 is density 1 (a gallery); index 9 is density 10 (a cockpit). All in rem.
SECTION_Y = (9.0, 8.0, 7.0, 6.0, 5.0, 4.25, 3.5, 3.0, 2.5, 2.0)
GAP = (2.5, 2.25, 2.0, 1.75, 1.5, 1.25, 1.1, 1.0, 0.875, 0.75)
ROW_H = (3.5, 3.25, 3.0, 2.75, 2.5, 2.375, 2.25, 2.125, 2.0, 1.875)


def _rem(value: float) -> str:
    return f"{round(value, 3):g}rem"


def measures(density: int) -> dict[str, float]:
    """The three measures of a density, in rem."""
    index = max(1, min(10, density)) - 1
    return {"section-y": SECTION_Y[index], "gap": GAP[index], "row-h": ROW_H[index]}


def render_rhythm_block(density: int) -> str:
    sizes = measures(density)
    lines = [
        "/* Ritmo vertical: sale de [structure] density (ver app/design_engine/rhythm.py). */",
        ":root {",
        f"  --kiro-section-y: {_rem(sizes['section-y'])};",
        f"  --kiro-gap: {_rem(sizes['gap'])};",
        f"  --kiro-row-h: {_rem(sizes['row-h'])};",
        "}",
        "@media (max-width: 767px) {",
        f"  :root {{ --kiro-section-y: {_rem(sizes['section-y'] * PHONE_SECTION_FACTOR)}; }}",
        "}",
    ]
    if sizes["row-h"] < TOUCH_ROW_REM:
        lines += [
            "@media (pointer: coarse) {",
            f"  :root {{ --kiro-row-h: {_rem(TOUCH_ROW_REM)}; }}",
            "}",
        ]
    lines += [
        "@utility section-y {",
        "  padding-block: var(--kiro-section-y);",
        "}",
        "@utility gap-rhythm {",
        "  gap: var(--kiro-gap);",
        "}",
        "@utility min-h-row {",
        "  min-height: var(--kiro-row-h);",
        "}",
    ]
    return render_block("rhythm", "\n".join(lines))
