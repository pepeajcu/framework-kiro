"""Compile the project's identity: `design.toml` into `input.css`, fonts and motion.

    make design build                  # apply everything; idempotent
    make design watch                  # rebuild whenever design.toml changes
    make design init preset=brutalista [primary="#DC2626"]
    make design set brand.primary="#0F766E" brand.neutral=warm
    make design-check                  # is what the toml says what the project ships?

The logic is in `app/design_engine/` (pure, typed, tested); this file is the I/O
around it: reading and writing files, and downloading what is missing.
"""

from __future__ import annotations

import argparse
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import httpx2

from app.branding import BrandError
from app.design_engine.checks import run_checks
from app.design_engine.compiler import Compiled, compile_contract
from app.design_engine.contract import (
    DesignContract,
    DesignError,
    contract_from_data,
    contract_to_data,
    dump_contract,
    load_contract,
)
from app.design_engine.fonts import MAX_FONT_BYTES, FontFile, validate_woff2
from app.design_engine.motion import missing_files
from app.design_engine.paths import Paths
from app.design_engine.presets import PRESETS, get_preset
from scripts.fetch import fetch_bytes

POLL_SECONDS = 0.5


@dataclass(frozen=True)
class BuildReport:
    contract: DesignContract
    compiled: Compiled
    downloaded: tuple[str, ...]
    changed: bool


# --- Pieces -----------------------------------------------------------------


def write_atomically(path: Path, text: str) -> None:
    """Replace `path` in one step, so a crash never leaves a half-written file."""
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(text, encoding="utf-8")
    temporary.replace(path)


def ensure_fonts(
    files: tuple[FontFile, ...], fonts_dir: Path, *, client: httpx2.Client | None = None
) -> tuple[str, ...]:
    """Download every font in `files` that is not on disk (or is not a valid woff2).

    A file already there and valid is left alone, so a rebuild works offline and
    a font you replaced by hand is not overwritten. Returns what was downloaded.
    """
    downloaded: list[str] = []
    for file in files:
        target = fonts_dir / file.filename
        if target.is_file():
            try:
                validate_woff2(target.read_bytes(), label=file.filename)
                continue
            except DesignError:
                pass  # corrupt: fall through and fetch it again
        data = fetch_bytes(
            file.url,
            limit=MAX_FONT_BYTES,
            label=f"{file.family} {file.weight}",
            client=client,
        )
        validate_woff2(data, label=f"{file.family} {file.weight}")
        fonts_dir.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        downloaded.append(file.filename)
    return tuple(downloaded)


def ensure_motion(
    level: int, paths: Paths, *, client: httpx2.Client | None = None
) -> tuple[str, ...]:
    """Make sure the scripts `level` needs are on disk; vendor the missing libraries."""
    if not missing_files(level, paths.static):
        return ()
    # Imported here: only a project that asks for level 7+ ever needs it.
    from scripts.motion import vendor_for_level

    written = vendor_for_level(level, paths.static, client=client)
    # What is still missing is a file of the framework itself, not a library: an
    # incomplete upgrade. Say so now rather than ship a page that loads nothing.
    still = missing_files(level, paths.static)
    if still:
        raise DesignError(
            f"motion.level = {level} necesita {', '.join(still)}, que viene con el framework "
            "(¿falta traerlo de upstream? ver docs/upgrading.md)"
        )
    return written


# --- Commands ---------------------------------------------------------------


def build(paths: Paths, *, client: httpx2.Client | None = None) -> BuildReport:
    """Apply `design.toml`: write `input.css`, fetch fonts, vendor motion libraries."""
    if not paths.contract.is_file():
        raise DesignError("no existe design.toml; créalo con `make design init`")
    contract = load_contract(paths.contract)
    css = paths.css.read_text(encoding="utf-8")
    compiled = compile_contract(contract, css)

    header = paths.headers / f"{contract.structure.header}.html"
    if not header.is_file():
        raise DesignError(
            f"structure.header = '{contract.structure.header}', pero no existe {header}"
        )

    # Everything that can fail goes before the write, so a failed download never
    # leaves `input.css` pointing at fonts that are not there.
    downloaded = ensure_fonts(compiled.fonts, paths.fonts, client=client)
    downloaded += ensure_motion(contract.motion.level, paths, client=client)

    changed = compiled.css != css
    if changed:
        write_atomically(paths.css, compiled.css)
    return BuildReport(contract, compiled, downloaded, changed)


def print_report(report: BuildReport, paths: Paths) -> None:
    contract, compiled = report.contract, report.compiled
    brand = contract.brand
    print(f"design.toml aplicado a {paths.css.relative_to(paths.root)}")
    print(
        f"  marca {brand.primary} · neutros {brand.neutral} · superficie {brand.surface} "
        f"· radio {brand.radius} · tema {contract.basecoat.theme}"
    )
    button = {
        p.mode: p.ratio
        for p in compiled.palette.pairs
        if (p.foreground, p.background) == ("--primary-foreground", "--primary")
    }
    for mode, ratio in button.items():
        name = "claro" if mode == "light" else "oscuro"
        print(f"  contraste del botón primario, modo {name}: {ratio:.1f}:1")
    for role, face in contract.typography.faces():
        print(f"  fuente {role}: {face.name} {', '.join(map(str, face.weights))}")
    print(f"  cabecera {contract.structure.header} · motion nivel {contract.motion.level}")
    if report.downloaded:
        print(f"  descargado: {', '.join(report.downloaded)}")
    if not report.changed:
        print("  (sin cambios: ya estaba al día)")
    for warning in compiled.warnings:
        print(f"aviso: {warning}", file=sys.stderr)


def init(paths: Paths, *, preset: str | None, primary: str | None, force: bool) -> None:
    """Write a `design.toml` from a style preset (or the defaults)."""
    if paths.contract.is_file() and not force and not load_contract(paths.contract).is_default:
        raise DesignError(
            "design.toml ya tiene una identidad propia; usa --force para sobrescribirla "
            "o `make design set …` para cambiar un valor"
        )
    contract = get_preset(preset).contract if preset else DesignContract()
    if primary:
        data = contract_to_data(contract)
        data["brand"]["primary"] = primary
        contract = contract_from_data(data)
    write_atomically(paths.contract, dump_contract(contract))
    label = f"estilo '{preset}'" if preset else "valores por defecto"
    print(f"design.toml creado con el {label}")


def set_values(paths: Paths, assignments: list[str]) -> None:
    """`brand.primary=#0F766E` style edits, validated as a whole before writing."""
    data = contract_to_data(load_contract(paths.contract))
    for assignment in assignments:
        key, separator, value = assignment.partition("=")
        parts = key.strip().split(".")
        if not separator or len(parts) != 2:
            raise DesignError(f"'{assignment}' no es válido; usa seccion.clave=valor")
        section, name = parts
        if section == "type" or section not in data or not isinstance(data[section], dict):
            raise DesignError(
                f"la sección '{section}' no se edita así; las fuentes se cambian con `make font`"
            )
        if name not in data[section]:
            raise DesignError(
                f"'{key}' no existe; claves de [{section}]: {', '.join(data[section])}"
            )
        data[section][name] = int(value) if name == "level" and value.isdigit() else value
    updated = contract_from_data(data)
    write_atomically(paths.contract, dump_contract(updated))


def check(paths: Paths, *, allow_defaults: bool) -> int:
    """Print every finding; the exit code is 1 if any is an error."""
    marks = {"ok": "✓", "warn": "!", "error": "✗"}
    findings = run_checks(paths, allow_defaults=allow_defaults)
    for finding in findings:
        stream = sys.stdout if finding.level == "ok" else sys.stderr
        print(f"  {marks[finding.level]} {finding.message}", file=stream)
        if finding.hint:
            print(f"      → {finding.hint}", file=stream)
    errors = sum(1 for f in findings if f.level == "error")
    warnings = sum(1 for f in findings if f.level == "warn")
    print(f"\n{errors} errores, {warnings} avisos")
    return 1 if errors else 0


def watch(paths: Paths) -> None:
    """Rebuild whenever design.toml changes. Run `make css-watch` beside it."""
    print(f"vigilando {paths.contract.name} (Ctrl+C para salir); `make css-watch` recompila el CSS")
    last: int | None = None
    while True:
        try:
            stamp = paths.contract.stat().st_mtime_ns
        except OSError:
            stamp = None
        if stamp != last:
            last = stamp
            try:
                print_report(build(paths), paths)
            except (BrandError, OSError) as exc:
                print(f"error: {exc}", file=sys.stderr)
        time.sleep(POLL_SECONDS)


# --- Entry point ------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("build", help="aplicar design.toml (input.css, fuentes, motion)")
    sub.add_parser("watch", help="recompilar al cambiar design.toml")

    init_parser = sub.add_parser("init", help="crear design.toml desde un estilo")
    init_parser.add_argument("--preset", choices=sorted(PRESETS), help="estilo de partida")
    init_parser.add_argument("--primary", help="color de marca, ej. #0F766E")
    init_parser.add_argument(
        "--force", action="store_true", help="sobrescribir un design.toml propio"
    )

    set_parser = sub.add_parser("set", help="cambiar valores: seccion.clave=valor")
    set_parser.add_argument("assignments", nargs="+")

    check_parser = sub.add_parser("check", help="validar el contrato contra el proyecto")
    check_parser.add_argument("--allow-defaults", action="store_true")

    args = parser.parse_args(argv)
    paths = Paths()
    try:
        if args.command == "build":
            print_report(build(paths), paths)
        elif args.command == "watch":
            watch(paths)
        elif args.command == "init":
            init(paths, preset=args.preset, primary=args.primary, force=args.force)
            print_report(build(paths), paths)
        elif args.command == "set":
            set_values(paths, args.assignments)
            print_report(build(paths), paths)
        else:
            return check(paths, allow_defaults=args.allow_defaults)
    except BrandError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
