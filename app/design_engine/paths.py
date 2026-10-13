"""Where the engine's files live. One place, so tests can point it at a tmp dir."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.design_engine.contract import CONTRACT_FILE

PROJECT_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Paths:
    """The project layout the design engine reads and writes."""

    root: Path = PROJECT_ROOT

    @property
    def contract(self) -> Path:
        return self.root / CONTRACT_FILE

    @property
    def design_md(self) -> Path:
        return self.root / "DESIGN.md"

    @property
    def static(self) -> Path:
        return self.root / "app" / "static"

    @property
    def css(self) -> Path:
        return self.static / "css" / "input.css"

    @property
    def fonts(self) -> Path:
        return self.static / "fonts"

    @property
    def basecoat(self) -> Path:
        return self.static / "css" / "vendor" / "basecoat"

    @property
    def templates(self) -> Path:
        return self.root / "app" / "templates"

    @property
    def headers(self) -> Path:
        return self.templates / "partials" / "headers"
