"""`make design-check`: validate the contract against the project, statically.

It answers one question: *is the identity this project declares the identity it
actually ships?* Each check below is a way that can silently stop being true:
the toml edited but not built, a font file deleted, an animation asked for that
the motion level does not provide, `DESIGN.md` saying one thing and the toml
another, or nothing chosen at all, which is how every Kiro project ends up
looking like every other one.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

from app.design_engine.blocks import find_block
from app.design_engine.compiler import compile_contract
from app.design_engine.contract import DesignContract, DesignError, load_contract
from app.design_engine.fonts import required_files, validate_woff2
from app.design_engine.motion import VOCABULARY, missing_files
from app.design_engine.paths import Paths

Level = Literal["ok", "warn", "error"]

_DATA_MOTION = re.compile(r"""data-motion\s*=\s*["']([A-Za-z0-9_-]+)["']""")
_JINJA_COMMENT = re.compile(r"\{#.*?#\}", re.DOTALL)
# `/_design` shows every value the level provides and gates each one on the level
# in its own template logic, which a text scan cannot evaluate.
SHOWCASE_TEMPLATE = "pages/design.html"
_EASE_SPRING = re.compile(r"""data-motion-ease\s*=\s*["']spring["']""")
SPRING_MIN_LEVEL = 7
_MOTION_DIAL = re.compile(r"MOTION_INTENSITY`?\s*\|\s*(\d+)")
_HEX = re.compile(r"#[0-9A-Fa-f]{6}\b|#[0-9A-Fa-f]{3}\b")


@dataclass(frozen=True)
class Finding:
    level: Level
    message: str
    hint: str | None = None


def _ok(message: str) -> Finding:
    return Finding("ok", message)


def _warn(message: str, hint: str | None = None) -> Finding:
    return Finding("warn", message, hint)


def _error(message: str, hint: str | None = None) -> Finding:
    return Finding("error", message, hint)


def run_checks(paths: Paths, *, allow_defaults: bool = False) -> list[Finding]:
    """Every finding, in the order they should be read. `error` fails the check."""
    if not paths.contract.is_file():
        return [_error("no existe design.toml", "créalo con `make design init`")]
    try:
        contract = load_contract(paths.contract)
    except DesignError as exc:
        return [_error(str(exc))]

    findings = [_ok("design.toml es válido")]
    findings += _check_defaults(contract, allow_defaults)
    findings += _check_compiled(contract, paths)
    findings += _check_theme(contract, paths)
    findings += _check_fonts(contract, paths)
    findings += _check_motion(contract, paths)
    findings += _check_header(contract, paths)
    findings += _check_templates(contract, paths)
    findings += _check_design_md(contract, paths)
    return findings


def _check_defaults(contract: DesignContract, allow_defaults: bool) -> list[Finding]:
    if not contract.is_default:
        return []
    if allow_defaults:
        return [
            _warn("design.toml sigue en los valores por defecto (permitido con --allow-defaults)")
        ]
    return [
        _error(
            "design.toml sigue en los valores por defecto: este proyecto se verá igual "
            "que cualquier otro Kiro",
            "elige una identidad con /kiro-init, o `make design init preset=<estilo>`",
        )
    ]


def _check_compiled(contract: DesignContract, paths: Paths) -> list[Finding]:
    css = paths.css.read_text(encoding="utf-8") if paths.css.is_file() else ""
    try:
        compiled = compile_contract(contract, css)
    except DesignError as exc:
        return [_error(str(exc))]

    pairs = [p for p in compiled.palette.pairs if p.required]
    worst = min(pairs, key=lambda p: p.ratio)
    findings = [_ok(f"contraste AA en {len(pairs)} combinaciones (el mínimo, {worst.ratio:.1f}:1)")]
    findings += [_warn(message) for message in compiled.warnings]

    pristine = contract.is_default and find_block(css, "brand") is None
    if compiled.css != css and not pristine:
        findings.append(
            _error(
                "app/static/css/input.css no está al día con design.toml",
                "ejecuta `make design build`",
            )
        )
    else:
        findings.append(_ok("input.css está al día con design.toml"))
    return findings


def _check_theme(contract: DesignContract, paths: Paths) -> list[Finding]:
    theme = paths.basecoat / f"basecoat-{contract.basecoat.theme}.css"
    if not theme.is_file():
        return [_error(f"el tema '{contract.basecoat.theme}' no está vendorizado ({theme.name})")]
    return [_ok(f"tema de Basecoat: {contract.basecoat.theme}")]


def _check_fonts(contract: DesignContract, paths: Paths) -> list[Finding]:
    files = required_files(contract.typography)
    findings: list[Finding] = []
    for file in files:
        path = paths.fonts / file.filename
        if not path.is_file():
            findings.append(
                _error(
                    f"falta la fuente {file.family} {file.weight}", "ejecuta `make design build`"
                )
            )
            continue
        try:
            validate_woff2(path.read_bytes(), label=file.filename)
        except DesignError as exc:
            findings.append(_error(str(exc), "bórrala y ejecuta `make design build`"))
    if files and not any(f.level == "error" for f in findings):
        findings.append(_ok(f"{len(files)} archivos de fuente presentes y válidos"))

    wanted = {file.filename for file in files}
    if paths.fonts.is_dir():
        orphans = sorted(p.name for p in paths.fonts.glob("*.woff2") if p.name not in wanted)
        findings += [
            _warn(f"fuente huérfana: {name} (design.toml ya no la usa)", "bórrala si sobra")
            for name in orphans
        ]
    return findings


def _check_motion(contract: DesignContract, paths: Paths) -> list[Finding]:
    level = contract.motion.level
    missing = missing_files(level, paths.static)
    if missing:
        return [
            _error(
                f"motion.level = {level} necesita {', '.join(missing)}",
                "ejecuta `make design build` (o `make motion level=…`)",
            )
        ]
    return [_ok(f"motion: nivel {level}, archivos presentes")]


def _check_header(contract: DesignContract, paths: Paths) -> list[Finding]:
    name = contract.structure.header
    if not (paths.headers / f"{name}.html").is_file():
        return [_error(f"no existe partials/headers/{name}.html")]
    return [_ok(f"cabecera: {name}")]


def _check_templates(contract: DesignContract, paths: Paths) -> list[Finding]:
    """`data-motion` values the project's level does not provide."""
    if not paths.templates.is_dir():
        return []
    level = contract.motion.level
    findings: list[Finding] = []
    seen: set[tuple[str, str]] = set()
    for path in sorted(paths.templates.rglob("*.html")):
        relative = path.relative_to(paths.templates)
        if relative.parts[0] in {"basecoat", "emails"} or relative.as_posix() == SHOWCASE_TEMPLATE:
            continue
        # A comment that documents `data-motion="pin"` is not a use of it.
        text = _JINJA_COMMENT.sub("", path.read_text(encoding="utf-8"))
        if _EASE_SPRING.search(text) and level < SPRING_MIN_LEVEL:
            findings.append(
                _warn(
                    f'{relative}: data-motion-ease="spring" pide motion.level >= '
                    f"{SPRING_MIN_LEVEL} y el proyecto está en {level}; entrará con la curva "
                    "normal",
                    "sube el nivel en design.toml o quita el atributo",
                )
            )
        for value in _DATA_MOTION.findall(text):
            if (str(relative), value) in seen:
                continue
            seen.add((str(relative), value))
            needed = VOCABULARY.get(value)
            if needed is None:
                findings.append(
                    _warn(
                        f'{relative}: data-motion="{value}" no existe',
                        "valores: " + ", ".join(VOCABULARY),
                    )
                )
            elif needed > level:
                findings.append(
                    _warn(
                        f'{relative}: data-motion="{value}" pide motion.level >= {needed} '
                        f"y el proyecto está en {level}; se verá estático",
                        "sube el nivel en design.toml o quita el atributo",
                    )
                )
    return findings


def _check_design_md(contract: DesignContract, paths: Paths) -> list[Finding]:
    if not paths.design_md.is_file():
        return [_warn("no existe DESIGN.md", "ejecuta /kiro-init")]
    text = paths.design_md.read_text(encoding="utf-8")
    if "TODO" in text:
        return [_warn("DESIGN.md todavía tiene TODO", "ejecuta /kiro-init")]

    findings: list[Finding] = []
    dial = _MOTION_DIAL.search(text)
    if dial and int(dial.group(1)) != contract.motion.level:
        findings.append(
            _warn(
                f"DESIGN.md dice MOTION_INTENSITY = {dial.group(1)} pero design.toml tiene "
                f"motion.level = {contract.motion.level}",
                "deben coincidir: uno de los dos está desactualizado",
            )
        )
    for line in text.splitlines():
        if "primario" in line.lower():
            hexes = {h.upper() for h in _HEX.findall(line)}
            if hexes and contract.brand.primary not in {_long(h) for h in hexes}:
                findings.append(
                    _warn(
                        f"DESIGN.md anota el primario como {', '.join(sorted(hexes))} pero "
                        f"design.toml tiene {contract.brand.primary}",
                        "deben coincidir",
                    )
                )
            break
    if not re.search(r"^#{2,3}\s*Firma visual", text, re.MULTILINE):
        findings.append(
            _warn(
                "DESIGN.md no declara una firma visual",
                "sin 2-3 gestos propios, el proyecto converge con otros del mismo estilo",
            )
        )
    if not findings:
        findings.append(_ok("DESIGN.md es coherente con design.toml"))
    return findings


def _long(value: str) -> str:
    """`#abc` to `#AABBCC`, so short and long hex compare equal."""
    value = value.upper()
    if len(value) == 4:
        return "#" + "".join(ch * 2 for ch in value[1:])
    return value
