"""The data behind `/_design`: the project's identity, laid out to be judged.

Everything here reads `design.toml` and derives from it; nothing is written. A
visitor can also *preview* a palette before choosing it, through query
parameters (`?style=brutalista`, `?primary=%230F766E&surface=cream`). Those
values are validated by the same models the compiler uses and the CSS is
generated from numbers, so nothing a visitor types is ever echoed into the page
as markup.
"""

from __future__ import annotations

from dataclasses import dataclass

from pydantic import ValidationError

from app.design_engine.contract import (
    Brand,
    DesignContract,
    DesignError,
    contract_to_data,
    load_contract,
)
from app.design_engine.palette import (
    Palette,
    derive_palette,
    format_ratio,
    render_palette_block,
)
from app.design_engine.paths import Paths
from app.design_engine.presets import PRESETS, Preset, get_preset

# Token groups, in the order a person reads a palette: surface, brand, state.
SWATCHES: tuple[tuple[str, str, str], ...] = (
    ("background", "--background", "--foreground"),
    ("card", "--card", "--card-foreground"),
    ("popover", "--popover", "--popover-foreground"),
    ("primary", "--primary", "--primary-foreground"),
    ("secondary", "--secondary", "--secondary-foreground"),
    ("muted", "--muted", "--muted-foreground"),
    ("accent", "--accent", "--accent-foreground"),
    ("destructive", "--destructive", "--background"),
    ("sidebar", "--sidebar", "--sidebar-foreground"),
)
LINES: tuple[tuple[str, str], ...] = (
    ("border", "--border"),
    ("input", "--input"),
    ("ring", "--ring"),
)


@dataclass(frozen=True)
class Swatch:
    name: str
    background: str
    foreground: str
    ratio_light: str | None
    ratio_dark: str | None


@dataclass(frozen=True)
class DesignPage:
    """What `pages/design.html` renders."""

    contract: DesignContract
    palette: Palette
    swatches: tuple[Swatch, ...]
    lines: tuple[tuple[str, str], ...]
    presets: tuple[Preset, ...]
    preview_css: str | None  # set only when the visitor asked to preview something
    preview_label: str | None
    error: str | None
    warnings: tuple[str, ...]


def _ratio(palette: Palette, mode: str, foreground: str, background: str) -> str | None:
    for pair in palette.pairs:
        if (pair.mode, pair.foreground, pair.background) == (mode, foreground, background):
            return format_ratio(pair.ratio, 1)
    return None


def _swatches(palette: Palette) -> tuple[Swatch, ...]:
    return tuple(
        Swatch(
            name,
            bg,
            fg,
            _ratio(palette, "light", fg, bg),
            _ratio(palette, "dark", fg, bg),
        )
        for name, bg, fg in SWATCHES
    )


def build_page(
    paths: Paths | None = None,
    *,
    style: str | None = None,
    overrides: dict[str, str] | None = None,
) -> DesignPage:
    """The page for the project's contract, optionally previewing another palette.

    `style` is a preset name; `overrides` are `[brand]` keys. Invalid input does
    not raise: the page renders the project's real identity with an `error`.
    """
    paths = paths or Paths()
    try:
        contract = load_contract(paths.contract)
    except DesignError as exc:
        contract = DesignContract()
        error: str | None = str(exc)
    else:
        error = None

    palette = derive_palette(contract.brand)
    preview_css: str | None = None
    label: str | None = None

    overrides = {key: value for key, value in (overrides or {}).items() if value}
    if style or overrides:
        try:
            base = get_preset(style).contract.brand if style else contract.brand
            data = base.model_dump()
            data.update(overrides)
            brand = Brand.model_validate(data)
            previewed = derive_palette(brand)
        except (DesignError, ValidationError) as exc:
            error = _preview_error(exc)
        else:
            palette = previewed
            preview_css = render_palette_block(previewed, radius=brand.radius)
            parts = [f"estilo {style}"] if style else []
            parts += [f"{key}={value}" for key, value in overrides.items()]
            label = ", ".join(parts)
            contract = DesignContract.model_validate(
                {**contract_to_data(contract), "brand": brand.model_dump()}
            )

    return DesignPage(
        contract=contract,
        palette=palette,
        warnings=_warnings(palette),
        swatches=_swatches(palette),
        lines=LINES,
        presets=tuple(PRESETS.values()),
        preview_css=preview_css,
        preview_label=label,
        error=error,
    )


def _warnings(palette: Palette) -> tuple[str, ...]:
    """What to flag about a palette: unreadable pairs first, then the softer notes."""
    failures = tuple(
        f"No cumple WCAG AA: {pair.describe()} da {format_ratio(pair.ratio)}:1 (mínimo 4.5). "
        "`make design build` se negaría a compilarla."
        for pair in palette.failures
    )
    return failures + palette.warnings


def _preview_error(exc: DesignError | ValidationError) -> str:
    if isinstance(exc, ValidationError):
        first = exc.errors()[0]
        where = ".".join(str(part) for part in first["loc"])
        return f"vista previa no válida ({where}): {first['msg'].removeprefix('Value error, ')}"
    return f"vista previa no válida: {exc}"
