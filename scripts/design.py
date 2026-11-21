"""Compile the project's identity: `design.toml` into `input.css`, fonts and motion.

    make design build                  # apply everything; idempotent
    make design watch                  # rebuild whenever design.toml changes
    make design init preset=brutalista [primary="#DC2626"]
    make design set brand.primary="#0F766E" brand.neutral=warm
    make design-check                  # is what the toml says what the project ships?
    make design-propose from=brief.json [base=advisor.json] [name=spa]
    make design-apply proposal=spa [force=1]

The logic is in `app/design_engine/` (pure, typed, tested); this file is the I/O
around it: reading and writing files, and downloading what is missing.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import shutil
import subprocess
import sys
import time
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

import httpx2

from app.branding import BrandError
from app.design_engine.advisor import brief_from_design_system, load_overlay
from app.design_engine.brief import (
    DesignBrief,
    Proposal,
    decision_lines,
    proposal_from_data,
    proposal_to_data,
    propose,
    provenance_entry,
    render_report,
)
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
from app.design_engine.design_md import (
    DECISIONS_HEADING,
    PROVENANCE_HEADING,
    add_lines,
    read_dials,
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
        if name == "allow":
            # `rules.allow=P1,P2` (an empty value clears the list)
            data[section][name] = [item.strip() for item in value.split(",") if item.strip()]
        else:
            numeric = name in ("level", "density") and value.isdigit()
            data[section][name] = int(value) if numeric else value
    updated = contract_from_data(data)
    write_atomically(paths.contract, dump_contract(updated))


_SLUG = re.compile(r"[^a-z0-9]+")


def _slug(text: str) -> str:
    return _SLUG.sub("-", text.lower()).strip("-")[:48] or "propuesta"


def _read_brief(path: Path) -> DesignBrief:
    try:
        return DesignBrief.model_validate_json(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise DesignError(f"no se puede leer {path}: {exc.strerror}") from exc
    except ValueError as exc:
        raise DesignError(f"{path} no es un brief válido:\n{exc}") from exc


def make_proposal(
    paths: Paths,
    *,
    source: Path | None,
    base: Path | None,
    name: str | None,
    fonts: Path | None = None,
    font_map: Mapping[str, str] | None = None,
    today: dt.date | None = None,
) -> tuple[str, Proposal]:
    """Translate briefs into `.design/proposals/<name>.{json,toml,md}`. Writes nothing else."""
    if source is None and base is None:
        raise DesignError("falta un brief: `make design-propose from=brief.json`")
    today = today or dt.datetime.now(tz=dt.UTC).date()
    inspiration = _read_brief(source) if source else None
    baseline = _read_brief(base) if base else None
    table: dict[str, str] = dict(font_map or {})
    if fonts is not None:
        try:
            table.update(json.loads(fonts.read_text(encoding="utf-8")))
        except (OSError, ValueError) as exc:
            raise DesignError(f"no se puede leer la tabla de fuentes {fonts}: {exc}") from exc

    current = load_contract(paths.contract)
    proposal = propose(base=baseline, inspiration=inspiration, current=current, fonts=table)

    chosen = inspiration or baseline
    assert chosen is not None
    slug = _slug(name or chosen.title or chosen.provenance)
    paths.proposals.mkdir(parents=True, exist_ok=True)
    write_atomically(
        paths.proposals / f"{slug}.json",
        json.dumps(proposal_to_data(proposal, today), indent=2, ensure_ascii=False) + "\n",
    )
    write_atomically(paths.proposals / f"{slug}.toml", dump_contract(proposal.contract))
    write_atomically(paths.proposals / f"{slug}.md", render_report(proposal, current, today))
    return slug, proposal


# What the advisor runs: uupm's own `search.py`, vendored. `-I` keeps the working
# directory and the user's site-packages out of its way; its own scripts folder is
# added by hand because `-I` drops it too.
_UUPM_RUNNER = (
    "import runpy, sys\n"
    "scripts = sys.argv[1]\n"
    "sys.path.insert(0, scripts)\n"
    "sys.argv = [scripts + '/search.py', *sys.argv[2:]]\n"
    "runpy.run_path(scripts + '/search.py', run_name='__main__')\n"
)
UUPM_DOMAINS = ("product", "style", "color", "landing", "ux", "typography", "chart")


def run_uupm(paths: Paths, args: list[str], *, timeout: float = 60.0) -> str:
    """Run uupm's search with the given arguments and return what it printed."""
    scripts = paths.uupm / "scripts"
    if not (scripts / "search.py").is_file():
        raise DesignError(
            "falta el asesor uupm (.claude/skills/kiro-design/uupm/); "
            "se trae con `uv run python -m scripts.vendor_uupm`"
        )
    command = [sys.executable, "-I", "-c", _UUPM_RUNNER, str(scripts), *args]
    try:
        # Our own vendored script, no shell, a fixed interpreter: nothing to inject into.
        result = subprocess.run(  # noqa: S603
            command, capture_output=True, text=True, timeout=timeout, check=False
        )
    except subprocess.TimeoutExpired as exc:
        raise DesignError(f"uupm tardó más de {timeout:g} s en responder") from exc
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip().splitlines()[-1:] or ["sin detalle"]
        raise DesignError(f"uupm falló: {detail[0]}")
    return result.stdout


def advise(
    paths: Paths, query: str, *, name: str | None, today: dt.date | None = None
) -> tuple[str, Proposal]:
    """Ask uupm for a design system for this product and turn it into a proposal.

    uupm is the **base**: it says what a product of this kind needs. The proposal
    is saved for review like any other; `make design-propose from=...
    base=.design/briefs/<name>.json` dresses it with a style on top.
    """
    today = today or dt.datetime.now(tz=dt.UTC).date()
    dials = (
        read_dials(paths.design_md.read_text(encoding="utf-8")) if paths.design_md.is_file() else {}
    )
    arguments = [query, "--design-system", "--json", "-p", name or query]
    for key, flag in (("variance", "--variance"), ("motion", "--motion"), ("density", "--density")):
        if key in dials:
            arguments += [flag, str(dials[key])]

    raw = run_uupm(paths, arguments)
    try:
        data = json.loads(raw)
    except ValueError as exc:
        raise DesignError("uupm no devolvió JSON válido") from exc

    advice = brief_from_design_system(data, load_overlay(paths.uupm_overlay), dials=dials)
    slug = _slug(name or advice.brief.title or query)
    for folder, payload in (
        ("uupm", json.dumps(data, indent=2, ensure_ascii=False)),
        ("briefs", advice.brief.model_dump_json(indent=2)),
    ):
        (paths.work / folder).mkdir(parents=True, exist_ok=True)
        write_atomically(paths.work / folder / f"{slug}.json", payload + "\n")
    return make_proposal(
        paths,
        source=None,
        base=paths.work / "briefs" / f"{slug}.json",
        name=slug,
        font_map=advice.fonts,
        today=today,
    )


def search_ux(paths: Paths, query: str, *, domain: str, stack: bool) -> str:
    """uupm's plain search: UX guidelines, charts, landing patterns... as text."""
    if domain not in UUPM_DOMAINS:
        raise DesignError(f"dominio '{domain}' no válido; opciones: {', '.join(UUPM_DOMAINS)}")
    arguments = [query, "--stack", "html-tailwind"] if stack else [query, "--domain", domain]
    return run_uupm(paths, [*arguments, "--max-results", "5"])


def apply_proposal(
    paths: Paths,
    slug: str,
    *,
    force: bool,
    today: dt.date | None = None,
    client: httpx2.Client | None = None,
) -> BuildReport:
    """Make a proposal the project's identity: design.toml, DESIGN.md, then a build.

    A project that already has an identity of its own is never overwritten
    without `force`, and a backup of what is replaced goes to `.design/backup/`.
    """
    today = today or dt.datetime.now(tz=dt.UTC).date()
    source = paths.proposals / f"{slug}.json"
    if not source.is_file():
        existing = sorted(p.stem for p in paths.proposals.glob("*.json"))
        listing = ", ".join(existing) if existing else "ninguna"
        raise DesignError(f"no existe la propuesta '{slug}'; hay: {listing}")
    try:
        proposal = proposal_from_data(json.loads(source.read_text(encoding="utf-8")))
    except ValueError as exc:
        raise DesignError(f"{source.name} no es JSON válido: {exc}") from exc

    current = load_contract(paths.contract)
    if not current.is_default and current != proposal.contract and not force:
        raise DesignError(
            "design.toml ya tiene una identidad propia; usa force=1 para sustituirla "
            "(se guarda una copia en .design/backup/)"
        )

    stamp = dt.datetime.now(tz=dt.UTC).strftime("%Y%m%d-%H%M%S")
    backup = paths.work / "backup" / stamp
    for original in (paths.contract, paths.design_md):
        if original.is_file():
            backup.mkdir(parents=True, exist_ok=True)
            shutil.copy2(original, backup / original.name)

    write_atomically(paths.contract, dump_contract(proposal.contract))
    if paths.design_md.is_file():
        text = paths.design_md.read_text(encoding="utf-8")
        text = add_lines(text, DECISIONS_HEADING, decision_lines(proposal, today))
        text = add_lines(text, PROVENANCE_HEADING, [provenance_entry(proposal, today)])
        write_atomically(paths.design_md, text)
    for item in proposal.unresolved:
        print(f"sin resolver: {item}", file=sys.stderr)
    return build(paths, client=client)


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

    propose_parser = sub.add_parser("propose", help="traducir un brief a una propuesta de contrato")
    propose_parser.add_argument(
        "--from", dest="source", type=Path, help="brief de inspiración (JSON)"
    )
    propose_parser.add_argument("--base", type=Path, help="brief de base del producto (JSON)")
    propose_parser.add_argument(
        "--fonts", type=Path, help="tabla JSON nombre de fuente → Fontsource"
    )
    propose_parser.add_argument("--name", help="nombre de la propuesta")

    apply_parser = sub.add_parser("apply", help="aplicar una propuesta guardada")
    apply_parser.add_argument("proposal", help="nombre de la propuesta")
    apply_parser.add_argument("--force", action="store_true", help="sustituir una identidad propia")

    advise_parser = sub.add_parser("advise", help="pedir a uupm un sistema de diseño y proponerlo")
    advise_parser.add_argument("query", help="el producto, ej. 'landing de un spa de lujo'")
    advise_parser.add_argument("--name", help="nombre de la propuesta")

    ux_parser = sub.add_parser("ux", help="consultar a uupm una guía (ux, chart, landing...)")
    ux_parser.add_argument("query")
    ux_parser.add_argument("--domain", default="ux", choices=UUPM_DOMAINS)
    ux_parser.add_argument("--stack", action="store_true", help="guías de html-tailwind")

    sub.add_parser("schema", help="imprimir el esquema JSON de un brief")

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
        elif args.command == "propose":
            slug, proposal = make_proposal(
                paths, source=args.source, base=args.base, name=args.name, fonts=args.fonts
            )
            print(f"propuesta '{slug}' guardada en {paths.proposals.relative_to(paths.root)}/")
            for decision in proposal.decisions:
                print(
                    f"  {decision.field}: {decision.before} → {decision.after} ({decision.reason})"
                )
            for item in proposal.unresolved:
                print(f"  sin resolver: {item}", file=sys.stderr)
            print(f"revísala y aplícala con `make design-apply proposal={slug}`")
        elif args.command == "schema":
            print(json.dumps(DesignBrief.model_json_schema(), indent=2, ensure_ascii=False))
        elif args.command == "advise":
            slug, proposal = advise(paths, args.query, name=args.name)
            print(f"uupm propone para '{args.query}'; guardado como '{slug}'")
            for decision in proposal.decisions:
                print(
                    f"  {decision.field}: {decision.before} → {decision.after} ({decision.reason})"
                )
            for note in proposal.ux_notes:
                print(f"  ux: {note}")
            review = f".design/proposals/{slug}.md"
            print(f"revisa {review} y aplica con `make design-apply proposal={slug}`")
        elif args.command == "ux":
            print(search_ux(paths, args.query, domain=args.domain, stack=args.stack))
        elif args.command == "apply":
            print_report(apply_proposal(paths, args.proposal, force=args.force), paths)
            return check(paths, allow_defaults=False)
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
