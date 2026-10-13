"""Compile a `DesignContract` into the project's `input.css`.

Pure: text in, text out. `scripts/design.py` does the I/O around it (reading
the contract and `input.css`, downloading missing fonts, writing the result).
"""

from __future__ import annotations

from dataclasses import dataclass

from app.branding import apply_brand_block
from app.design_engine.blocks import (
    apply_block,
    apply_theme_block,
    remove_block,
    render_block,
)
from app.design_engine.contract import DesignContract, DesignError
from app.design_engine.fonts import FontFile, render_fonts_block_body, required_files
from app.design_engine.palette import (
    Palette,
    derive_palette,
    format_ratio,
    render_palette_block,
    suggest_primary,
)


@dataclass(frozen=True)
class Compiled:
    """The result of a compilation."""

    css: str
    palette: Palette
    fonts: tuple[FontFile, ...]
    warnings: tuple[str, ...]


def _contrast_error(contract: DesignContract, palette: Palette) -> DesignError:
    lines = ["La paleta no cumple WCAG AA (4.5:1) en estas combinaciones:"]
    for pair in palette.failures:
        lines.append(f"  - {pair.describe()}: {format_ratio(pair.ratio)}:1")

    brand = contract.brand
    failing = {(p.foreground, p.background) for p in palette.failures}
    if ("--primary-foreground", "--primary") in failing:
        suggestion = suggest_primary(brand.primary)
        if suggestion:
            lines.append(
                f"El texto de los botones no se lee sobre brand.primary = {brand.primary}. "
                f"Prueba {suggestion}: conserva el tono y sí cumple."
            )
    if brand.secondary and ("--secondary-foreground", "--secondary") in failing:
        suggestion = suggest_primary(brand.secondary)
        if suggestion:
            lines.append(f"Lo mismo con brand.secondary = {brand.secondary}; prueba {suggestion}.")
    return DesignError("\n".join(lines))


def compile_contract(contract: DesignContract, css: str) -> Compiled:
    """Apply `contract` to the text of `input.css`.

    Raises `DesignError` if the palette cannot be read (WCAG AA) or `css` has
    lost the anchors the blocks hang from. The result is a function of the
    contract alone: compiling the output again returns it unchanged.
    """
    palette = derive_palette(contract.brand)
    if palette.failures:
        raise _contrast_error(contract, palette)

    brand = contract.brand
    source = f"design.toml · {brand.primary} · {brand.neutral} · {brand.surface}"
    out = apply_theme_block(css, contract.basecoat.theme)
    out = apply_brand_block(out, render_palette_block(palette, radius=brand.radius, source=source))

    body = render_fonts_block_body(contract.typography)
    out = (
        remove_block(out, "fonts")
        if body is None
        else apply_block(out, "fonts", render_block("fonts", body))
    )

    warnings = list(palette.warnings)
    for advisory in palette.advisories:
        warnings.append(
            f"{advisory.describe()}: {format_ratio(advisory.ratio)}:1. Usado como texto (enlaces, "
            "`btn link`) no llega a AA; úsalo en rellenos y bordes"
        )
    return Compiled(
        css=out,
        palette=palette,
        fonts=required_files(contract.typography),
        warnings=tuple(warnings),
    )
